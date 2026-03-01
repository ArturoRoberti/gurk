from enum import Enum, auto
from typing import TypedDict


class _ScriptExtension(Enum):
    """Enumeration of supported script file extensions."""

    # fmt: off
    BASH   = "bash"
    PYTHON = "py"
    # fmt: on


class ScriptBlockTypes(Enum):
    """Types of top-level script blocks."""

    # fmt: off
    CLASS      = auto()
    FUNCTION   = auto()
    ENTRYPOINT = auto()
    IMPORT     = auto()
    OTHER      = auto()
    # fmt: on

    def __repr__(self):
        return self.name


class ScriptBlock(TypedDict):
    """Information about a top-level script block."""

    # fmt: off
    type:  ScriptBlockTypes
    name:  str | None
    lines: tuple[int, int]  # (start_line, end_line)
    # fmt: on
