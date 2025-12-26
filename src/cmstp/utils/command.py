import shutil
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Optional

from cmstp.utils.common import PIPX_PYTHON_PATH, FilePath
from cmstp.utils.patterns import PatternCollection


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


@dataclass(frozen=True)
class Command:
    """Represents a command to be executed, including its script and optional function."""

    # fmt: off
    script:   str           = field()
    function: Optional[str] = field(default=None)
    # fmt: on

    def __post_init__(self) -> None:
        # Check 'script'
        if not Path(self.script).exists():
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
        if self.function is not None:
            # Find function in script
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
                arg_list = [a.strip() for a in args.split(",") if a.strip()]
                if not (
                    len(arg_list) == 1 and arg_list[0].split(":")[0] == "*args"
                ):
                    raise ValueError(
                        f"'{self.function}' function in script "
                        f"{self.script} must ONLY capture '*args' as "
                        f"an argument, if it is to be used as a task",
                    )
        else:
            # Find entrypoint in script
            entrypoint_pattern = PatternCollection[self.kind.name].patterns[
                "entrypoint"
            ]
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
