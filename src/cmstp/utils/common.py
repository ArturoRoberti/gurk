import os
import re
import shutil
import sys
from enum import Enum
from importlib import resources
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import Optional, Union

from cmstp.cli.utils import CORE_COMMANDS
from cmstp.utils.patterns import PatternCollection

PACKAGE_SRC_PATH = Path(resources.files("cmstp")).expanduser().resolve()
PACKAGE_CONFIG_PATH = PACKAGE_SRC_PATH / "config"
DEFAULT_CONFIG_FILE = PACKAGE_CONFIG_PATH / "default.yaml"
ENABLED_CONFIG_FILE = PACKAGE_CONFIG_PATH / "enabled.yaml"
PACKAGE_TESTS_PATH = PACKAGE_SRC_PATH.parents[1] / "tests"
PIPX_PYTHON_PATH = Path(sys.executable)


FilePath = Union[Path, str]


def generate_random_path(
    suffix: Optional[str] = None,
    prefix: Optional[str] = None,
    create: bool = False,
) -> Path:
    """
    Generate a random temporary file or directory path.

    :param suffix: Suffix for the temporary file or directory
    :type suffix: Optional[str]
    :param prefix: Prefix for the temporary file or directory
    :type prefix: Optional[str]
    :param create: Whether to create the file or directory
    :type create: bool
    :return: Path to the temporary file or directory
    :rtype: Path
    """
    if suffix is not None and suffix.startswith("."):
        # File
        fd, path = mkstemp(suffix, prefix)
        os.close(fd)
        if not create:
            os.remove(path)
    else:
        # Directory
        path = mkdtemp(suffix, prefix)
        if not create:
            shutil.rmtree(path)

    return Path(path)


def resolve_package_path(raw_script: FilePath) -> Optional[FilePath]:
    """
    Resolve paths that may refer to package resources. Package paths are in the format:
    ```
    package://<package-name>/relative/path/inside/package
    ```
    The `package://` pattern does not need to be at the start of the string, and can appear
    multiple times in the string, but only the first occurrence of it is replaced.

    :param raw_script: Raw script path
    :type raw_script: FilePath
    :return: Resolved script path or None if package not found. The output type matches the input type.
    :rtype: FilePath | None
    """
    # Return wrong types as-is
    if not isinstance(raw_script, (Path, str)):
        return raw_script

    raw_str = str(raw_script)

    def _replace_package(match: re.Match) -> str:
        pkg_name, rel_path = match.groups()
        try:
            pkg_root = Path(resources.files(pkg_name))
        except ModuleNotFoundError:
            raise

        return str(pkg_root / rel_path)

    try:
        # Replace ALL occurrences of package://... anywhere in the string
        resolved_str = PatternCollection.PATH.patterns["package"].sub(
            _replace_package, raw_str
        )
    except ModuleNotFoundError:
        return None

    # NOTE: We use 'os' and no built-in 'Path' method to retain consecutive slashes
    resolved_str = os.path.expanduser(resolved_str)

    # Return same type as input
    if isinstance(raw_script, Path):
        return Path(resolved_str)
    else:
        return resolved_str


def stream_print(text: str, stderr: bool = False) -> None:
    """
    Print text to stdout or stderr.

    :param text: Text to be printed
    :type text: str
    :param stderr: Whether to print to stderr instead of stdout
    :type stderr: bool
    """
    if stderr:
        print(text, file=sys.stderr)
    else:
        print(text)


class ScriptExtension(Enum):
    """Enumeration of supported script file extensions."""

    # fmt: off
    BASH   = "bash"
    PYTHON = "py"
    # fmt: on


class CommandKind(Enum):
    """Enumeration of supported command kinds with their executables."""

    # fmt: off
    BASH   = shutil.which("bash")
    PYTHON = str(PIPX_PYTHON_PATH)
    # fmt: on

    @property
    def exe(self) -> str:
        return self.value

    @property
    def ext(self) -> str:
        try:
            return ScriptExtension[self.name].value
        except KeyError:
            raise ValueError(f"Unsupported CommandKind: {self.name}")

    @staticmethod
    def from_script(script: FilePath) -> "CommandKind":
        """
        Determine the command kind based on the script file extension.

        :param script: Path to the script file
        :type script: FilePath
        :return: CommandKind corresponding to the script type
        :rtype: CommandKind
        """
        suffix = Path(script).suffix.replace(".", "")
        return CommandKind[ScriptExtension(suffix).name]


SCRIPT_LANGUAGES = [kind.name for kind in CommandKind]


def get_script_path(script: FilePath, command: str) -> Path:
    """
    Create a full path to a script inside the package's scripts directory.

    :param script: Name of the script file
    :type script: FilePath
    :param command: Name of the command that uses the script
    :type command: str
    :return: Full path to the script file
    :rtype: Path
    """
    if not isinstance(script, (str, Path)):
        raise TypeError("script must be a str or Path")

    if command not in CORE_COMMANDS:
        raise ValueError(f"Unknown command: {command}")

    language = CommandKind.from_script(script).name.lower()
    return PACKAGE_SRC_PATH / "scripts" / language / command / script


def get_config_path(config_file: FilePath, command: str) -> Path:
    """
    Create a full path to a config file inside the package's config directory.

    :param config_file: Name of the config file
    :type config_file: FilePath
    :param command: Name of the command that uses the config file
    :type command: str
    :return: Full path to the config file
    :rtype: Path
    """
    if not isinstance(config_file, (str, Path)):
        raise TypeError("config_file must be a str or Path")

    if command not in CORE_COMMANDS:
        raise ValueError(f"Unknown command: {command}")

    return PACKAGE_CONFIG_PATH / command / config_file
