import shutil
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Optional

from cmstp.utils.common import PIPX_PYTHON_PATH, FilePath


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
        if self == CommandKind.BASH:
            return "bash"
        elif self == CommandKind.PYTHON:
            return "py"
        else:
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
        bash_suffixes = (".sh", ".bash")
        python_suffixes = (".py",)

        suffix = Path(script).suffix
        if suffix in bash_suffixes:
            return CommandKind.BASH
        elif suffix in python_suffixes:
            return CommandKind.PYTHON
        else:
            raise ValueError(
                f"Unsupported script type: {suffix} (supported: {bash_suffixes + python_suffixes})"
            )


@dataclass(frozen=True)
class Command:
    """Represents a command to be executed, including its script and optional function."""

    # fmt: off
    script:   str           = field()
    function: Optional[str] = field(default=None)
    # fmt: on

    @cached_property
    def kind(self) -> CommandKind:
        return CommandKind.from_script(self.script)

    def __str__(self) -> str:
        func_suffix = f"@{self.function}" if self.function else ""
        return f"{Path(self.script).stem}{func_suffix}"
