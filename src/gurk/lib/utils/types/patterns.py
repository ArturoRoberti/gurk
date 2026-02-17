import re
from enum import Enum
from typing import Protocol, TypedDict, TypeVar


class _PatternFactory(Protocol):
    """Callable that produces a regex pattern based on progress flag."""

    def __call__(self, *, progress: bool, warning: bool = False) -> re.Pattern:
        ...


def _pattern_factory(base_type: str) -> _PatternFactory:
    """
    Create a pattern factory for step patterns based on the base type.

    :param base_type: Base type of the pattern ('any', 'output', or 'comment')
    :type base_type: str
    :return: Pattern factory function
    :rtype: PatternFactory
    """

    def _factory(*, progress: bool, warning: bool = False) -> re.Pattern:
        """
        Generate a regex pattern for step messages.

        :param progress: Whether the step indicates progress
        :type progress: bool
        :param warning: Whether the step indicates a warning
        :type warning: bool
        :return: Compiled regex pattern for the step message
        :rtype: Pattern
        :raises ValueError: If an unknown base_type is provided
        """
        step_type = "STEP"
        if not progress:
            step_type += "_NO_PROGRESS"
        if warning:
            step_type += "_WARNING"

        if base_type == "any":
            pattern = rf"^.*__{step_type}__:(.*)$"
        elif base_type == "output":
            pattern = rf"^__{step_type}__:(.*)$"
        elif base_type == "comment":
            pattern = rf"^\s*#\s*\({step_type}\)\s*(.*)$"
        else:
            raise ValueError(f"Unknown base_type: {base_type}")

        return re.compile(pattern)

    return _factory


class _StepPatterns(TypedDict):
    """Patterns for different step message types."""

    # fmt: off
    any:     _PatternFactory
    output:  _PatternFactory
    comment: _PatternFactory
    # fmt: on


class _ScriptPatterns(TypedDict):
    """Patterns for different script types."""

    # fmt: off
    ENTRYPOINT: re.Pattern
    FUNCTION:   re.Pattern
    CLASS:      re.Pattern | None
    IF:         re.Pattern
    ELIF:       re.Pattern
    ELSE:       re.Pattern
    CASE:       re.Pattern | None
    FOR:        re.Pattern
    WHILE:      re.Pattern
    UNTIL:      re.Pattern | None
    IMPORT:     re.Pattern | None
    # fmt: on


class _PathPatterns(TypedDict):
    """Patterns for different path types."""

    # fmt: off
    symlink: re.Pattern
    package: re.Pattern
    # fmt: on


T = TypeVar("T")


class _EnumValue(Protocol[T]):
    """Protocol for enum values containing patterns."""

    patterns: T


# TODO: Use direct instantiation e.g. _StepPatterns(any=...), and remove _EnumValue?
class PatternCollection(Enum):
    """Collection of regex patterns for various utilities."""

    # fmt: off
    STEP: _EnumValue[_StepPatterns] = {
        "any":        _pattern_factory("any"),
        "output":     _pattern_factory("output"),
        "comment":    _pattern_factory("comment"),
    }
    BASH: _EnumValue[_ScriptPatterns] = {
        "ENTRYPOINT": re.compile(r"if\s+\[\[.*BASH_SOURCE.*\]\];?\s*"),
        "FUNCTION":   re.compile(r"\s*(?:function\s+|)(\w+)\s*\(\)\s*{\s*$"),
        "CLASS":      None,  # Bash has no classes
        "IF":         re.compile(r"^\s*if\s+(.*);\s*then\s*$"),
        "ELIF":       re.compile(r"^\s*elif\s+(.*);\s*then\s*$"),
        "ELSE":       re.compile(r"^\s*else\s*$"),
        "CASE":       re.compile(r"^\s*case\s+(.*)\s*in\s*$"),
        "FOR":        re.compile(r"^\s*for\s+(.*);\s*do\s*$"),
        "WHILE":      re.compile(r"^\s*while\s+(.*);\s*do\s*$"),
        "UNTIL":      re.compile(r"^\s*until\s+(.*);\s*do\s*$"),
        "IMPORT":     re.compile(r'^\s*source\s+(.+?)(?:\s*(?:#|;|$))'),
    }
    PYTHON: _EnumValue[_ScriptPatterns] = {
        "ENTRYPOINT": re.compile(r'if __name__\s*==\s*[\'"]__main__[\'"]\s*:'),
        "FUNCTION":   re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?\s*:\s*$"),
        "CLASS":      re.compile(r"^\s*class\s+(\w+)\s*(\(.*\))?:\s*$"),
        "IF":         re.compile(r"^\s*if\s+(.*):\s*$"),
        "ELIF":       re.compile(r"^\s*elif\s+(.*):\s*$"),
        "ELSE":       re.compile(r"^\s*else\s*:\s*$"),
        "CASE":       None,  # Python has no "case"
        "FOR":        re.compile(r"^\s*for\s+(.*):\s*$"),
        "WHILE":      re.compile(r"^\s*while\s+(.*):\s*$"),
        "UNTIL":      None,  # Python has no "until"
        "IMPORT":     None,  # Handled via ast module
    }
    PATH: _EnumValue[_PathPatterns] = {
        "package":     re.compile(r"package://([^/]+)/(.*?)"),
        "symlink":     re.compile(r"^symlink://(.*)$"),
    }
    ANSI:           _EnumValue[re.Pattern] = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    TRACEBACK_FILE: _EnumValue[re.Pattern] = re.compile(r'^\s*File\s+"([^"]+)",\s+line\s+(\d+)')
    NAMING:         _EnumValue[re.Pattern] = re.compile(r"^[A-Za-z_-]+$")
    # fmt: on

    @property
    def patterns(self) -> T:
        return self.value
