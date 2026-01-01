# TODO: Merge with utils/command.py

import os
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
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
        "package://<package-name>/relative/path/inside/package"

    :param raw_script: Raw script path
    :type raw_script: FilePath
    :return: Resolved script path or None if package not found. The output type matches the input type.
    :rtype: FilePath | None
    """
    # Return wrong types as-is
    if not isinstance(raw_script, (Path, str)):
        return raw_script

    # Resolve package paths
    match = PatternCollection.PATH.patterns["package"].match(str(raw_script))
    if match:
        pkg_name, rel_path = match.groups()
        try:
            resolved_path = Path(resources.files(pkg_name)) / rel_path
        except ModuleNotFoundError:
            return None
    else:
        # NOTE: We use 'os' and no built-in 'Path' method to retain '<type>://' multiple slashes
        resolved_path = os.path.expanduser(str(raw_script))

    # Return same type as input
    if isinstance(raw_script, Path):
        return Path(resolved_path)
    else:  # str
        return str(resolved_path)


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


@dataclass(frozen=True)
class Command:
    """Represents a command to be executed, including its script and optional function."""

    # fmt: off
    script:     str           = field()
    function:   Optional[str] = field(default=None)
    check_func: bool          = field(default=True)
    # fmt: on

    # TODO: Remove checks completely, as checked in pytest?
    #       Or does that rely on this resp. is a second check good to have?
    def __post_init__(self) -> None:
        # Check 'script'
        if not Path(self.script).is_file():
            raise FileNotFoundError(f"Script file not found: {self.script}")
        try:
            self.kind  # Trigger kind property to validate script type
        except ValueError:
            raise ValueError(
                f"Unsupported script type for file {self.script} - supported "
                f"types: {[ext.name.lower() for ext in ScriptExtension]}"
            )

        # Read script
        with open(self.script) as f:
            lines = f.readlines()

        # Check 'function'
        if self.check_func:
            if self.function is not None:
                # Find function in script
                # TODO: Does this also detect sub-functions? It should not
                # TODO: Use 'get_block_spans'?
                function_pattern = PatternCollection[self.kind.name].patterns[
                    "blocks"
                ]["FUNCTION"]
                function_matches = [
                    match.groups()
                    for line in lines
                    if (match := function_pattern.search(line.strip()))
                ]
                if self.kind == CommandKind.PYTHON:  # Also capture args
                    function_names = [name for name, _ in function_matches]
                else:  # No args are captured in bash
                    function_names = [name for name, in function_matches]
                if self.function not in function_names:
                    raise ValueError(
                        f"'{self.function}' function not found in script "
                        f"{self.script}\nAvailable functions: {function_names}",
                    )

                # If Python, check function definition only captures '*args'
                if self.kind == CommandKind.PYTHON:
                    # Test if the function has only *args
                    function_args = [args for _, args in function_matches]
                    args = function_args[function_names.index(self.function)]
                    arg_list = [
                        a.strip() for a in args.split(",") if a.strip()
                    ]
                    if not (
                        len(arg_list) == 1
                        and arg_list[0].split(":")[0] == "*args"
                    ):
                        raise ValueError(
                            f"'{self.function}' function in script "
                            f"{self.script} must ONLY capture '*args' as "
                            f"an argument, if it is to be used as a task",
                        )
            else:
                # Find entrypoint in script
                entrypoint_pattern = PatternCollection[
                    self.kind.name
                ].patterns["entrypoint"]
                entrypoint_matches = [
                    line
                    for line in lines
                    if entrypoint_pattern.search(line.strip())
                ]
                if len(entrypoint_matches) != 1:
                    raise ValueError(
                        f"Expected exactly one entrypoint, found {len(entrypoint_matches)}"
                    )

    @cached_property
    def kind(self) -> CommandKind:
        return CommandKind.from_script(self.script)

    def __str__(self) -> str:
        func_suffix = f"@{self.function}" if self.function else ""
        return f"{Path(self.script).stem}{func_suffix}"
