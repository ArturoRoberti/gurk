from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from gurk.lib.utils import PathLike

from .blocks import get_block_spans
from .command_kind import CommandKind
from .script_types import ScriptBlockTypes, _ScriptExtension


@dataclass(frozen=True)
class Command:
    """Represents a command to be executed, including its script and optional function."""

    # fmt: off
    script:     PathLike      = field()
    function:   None | str    = field(default=None)
    check_func: bool          = field(default=True)
    # fmt: on

    def __post_init__(
        self,
    ) -> (
        None
    ):  # TODO: Make "check_command" a separate function, then group with CommandKind?
        # Check 'script'
        if not Path(self.script).is_file():
            raise FileNotFoundError(f"Script file not found: {self.script}")
        try:
            self.kind  # Trigger 'kind' property to validate script type
        except ValueError:
            raise ValueError(
                f"Unsupported script type for file {self.script} - supported "
                f"types: {[ext.name.lower() for ext in _ScriptExtension]}"
            )

        # Check 'function'
        blocks = get_block_spans(self.script)
        if self.check_func and self.function is not None:
            available_functions = [
                b["name"]
                for b in blocks
                if b["type"] == ScriptBlockTypes.FUNCTION
            ]
            if self.function not in available_functions:
                raise FileNotFoundError(
                    f"'{self.function}' function not found in script "
                    f"{self.script}\nAvailable functions: {available_functions}",
                )

    @cached_property
    def kind(self) -> CommandKind:
        return CommandKind.from_script(self.script)

    def __str__(self) -> str:
        func_suffix = f"@{self.function}" if self.function else ""
        return f"{Path(self.script).stem}{func_suffix}"


@dataclass(frozen=True)
class SchedulerTask:
    """Represents a final task to be run by the scheduler"""

    # fmt: off
    name:        str             = field()
    command:     Command         = field()
    config_file: None | str      = field(default=None)
    depends_on:  tuple[str, ...] = field(default_factory=tuple)
    privileged:  bool            = field(default=False)
    args:        tuple[str, ...] = field(default_factory=tuple)
    # fmt: on
