import shutil
from enum import Enum
from pathlib import Path

from gurk.lib.utils import PIPX_PYTHON_PATH, PathLike

from .script_types import _ScriptExtension


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
            return _ScriptExtension[self.name].value
        except KeyError:
            raise ValueError(f"Unsupported CommandKind: {self.name}")

    @staticmethod
    def from_script(script: PathLike) -> "CommandKind":
        """
        Determine the command kind based on the script file extension.

        :param script: Path to the script file
        :type script: PathLike
        :return: CommandKind corresponding to the script type
        :rtype: CommandKind
        """
        if not (isinstance(script, Path) or isinstance(script, str)):
            raise ValueError(
                f"Expected script to be a Path, got {type(script)}"
            )

        suffix = Path(script).suffix.replace(".", "")
        return CommandKind[_ScriptExtension(suffix).name]
