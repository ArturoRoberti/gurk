import json
import os
import re
import shutil
import sys
from enum import Enum
from functools import cache, wraps
from importlib import resources
from importlib.metadata import Distribution
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import TypeAlias, TypeVar

from packaging.version import InvalidVersion, Version
from pydantic import ConfigDict, ValidationError, validate_call

from gurk.lib.utils.patterns import PatternCollection

PACKAGE_NAME = "gurk"
PACKAGE_SRC_PATH = Path(resources.files(PACKAGE_NAME)).expanduser().resolve()
PACKAGE_TESTS_PATH = PACKAGE_SRC_PATH.parents[1] / "tests"
PIPX_PYTHON_PATH = Path(sys.executable)
PACKAGE_HOME_PATH = Path.home() / f".{PACKAGE_NAME}"
PACKAGE_VENVS_PATH = PACKAGE_HOME_PATH / "venvs"
PACKAGE_CACHE_PATH = Path.home() / ".cache" / PACKAGE_NAME
SETUP_DONE_FILE = PACKAGE_HOME_PATH / "setup.done"


PACKAGE_VENVS_PATH.mkdir(parents=True, exist_ok=True)
PACKAGE_CACHE_PATH.mkdir(parents=True, exist_ok=True)


PathLike: TypeAlias = str | Path

T = TypeVar("T")
ListOrTuple: TypeAlias = list[T] | tuple[T, ...]

YES_ANSWERS = ["y", "yes", "true", "1"]
NO_ANSWERS = ["n", "no", "false", "0"]


@cache
def _is_typecheck_active() -> bool:
    # (Priority) Check environment variable override
    gurk_typecheck = os.getenv("GURK_TYPECHECK")
    if gurk_typecheck in YES_ANSWERS:
        return True
    elif gurk_typecheck in NO_ANSWERS:
        return False
    else:
        # See if the package is installed in editable mode
        try:
            direct_url = Distribution.from_name(PACKAGE_NAME).read_text(
                "direct_url.json"
            )
            return (
                json.loads(direct_url)
                .get("dir_info", {})
                .get("editable", False)
            )
        except Exception:
            return False


class InputValidationError(BaseException):
    """Custom error type for input validation errors in typecheck."""

    pass


_typecheck = validate_call(
    config=ConfigDict(
        strict=True, extra="forbid", arbitrary_types_allowed=True
    )
)


def typecheck(func):
    """
    Decorator to perform runtime type checking on function inputs using Pydantic's validate_call.
    It also formats validation errors to include the offending input type and value for easier debugging.
    """
    if not _is_typecheck_active():
        return func

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return _typecheck(func)(*args, **kwargs)
        except ValidationError as e:
            # Format errors with the offending input type/value for easier debugging
            messages = []
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                bad_input = err.get("input", "<missing>")
                bad_type = type(bad_input).__name__
                # Limit repr length to keep messages compact
                bad_repr = repr(bad_input)
                if len(bad_repr) > 200:
                    bad_repr = bad_repr[:197] + "..."
                messages.append(
                    f"{loc}: {err['msg']} (got {bad_type}: {bad_repr})"
                )
            raise InputValidationError(
                "Wrong input(s) to '"
                + func.__name__
                + "':\n"
                + "\n".join(messages)
            ) from None

    return wrapper


@typecheck
def generate_random_path(
    suffix: str | None = None,
    prefix: str | None = None,
    create: bool = False,
) -> Path:
    """
    Generate a random temporary file if an extension is
    provided in the suffix, else a directory path.

    :param suffix: Suffix for the temporary file or directory
    :type suffix: str | None
    :param prefix: Prefix for the temporary file or directory
    :type prefix: str | None
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


@typecheck
def resolve_package_path(raw_script: PathLike) -> PathLike | None:
    """
    Resolve paths that may refer to package resources. Package paths are in the format:
    ```
    package://<package-name>/relative/path/inside/package
    ```
    The `package://` pattern does not need to be at the start of the string, and can appear
    multiple times in the string, but only the first occurrence of it is replaced.

    :param raw_script: Raw script path
    :type raw_script: PathLike
    :return: Resolved script path or None if package not found. The output type matches the input type.
    :rtype: PathLike | None
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
        """Get the executable associated with the command kind."""
        return self.value

    @property
    def ext(self) -> str:
        """
        Get the file extension associated with the command kind.

        :param self: Instance of CommandKind
        :return: File extension as a string
        :rtype: str
        :raises ValueError: If the CommandKind is unsupported
        """
        try:
            return ScriptExtension[self.name].value
        except KeyError:
            raise ValueError(f"Unsupported CommandKind: {self.name}")

    @staticmethod
    @typecheck
    def from_script(script: PathLike) -> "CommandKind":
        """
        Determine the command kind based on the script file extension.

        :param script: Path to the script file
        :type script: PathLike
        :return: CommandKind corresponding to the script type
        :rtype: CommandKind
        """
        suffix = Path(script).suffix.replace(".", "")
        return CommandKind[ScriptExtension(suffix).name]


SCRIPT_LANGUAGES = [kind.name for kind in CommandKind]


@typecheck
def check_version(version: str) -> bool:
    """
    Check if the given version string conforms to semantic versioning.

    :param version: The version string to check.
    :type version: str
    :return: True if valid, False otherwise.
    :rtype: bool
    """
    try:
        Version(version)
        return True
    except InvalidVersion:
        return False
