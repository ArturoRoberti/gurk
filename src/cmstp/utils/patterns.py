import re
from enum import Enum
from typing import Optional, Protocol, TypedDict, TypeVar


class PatternFactory(Protocol):
    """Callable that produces a regex pattern based on progress flag."""

    def __call__(self, *, progress: bool, warning: bool = False) -> re.Pattern:
        ...


def pattern_factory(base_type: str) -> PatternFactory:
    """
    Create a pattern factory for step patterns based on the base type.

    :param base_type: Base type of the pattern ('any', 'output', or 'comment')
    :type base_type: str
    :return: Pattern factory function
    :rtype: PatternFactory
    """

    def factory(*, progress: bool, warning: bool = False) -> re.Pattern:
        """
        Generate a regex pattern for step messages.

        :param progress: Whether the step indicates progress
        :type progress: bool
        :return: Compiled regex pattern for the step message
        :rtype: Pattern
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

    return factory


class StepPatterns(TypedDict):
    """Patterns for different step message types."""

    # fmt: off
    any:     PatternFactory
    output:  PatternFactory
    comment: PatternFactory
    # fmt: on


class ScriptPatterns(TypedDict):
    """Patterns for different script types."""

    # fmt: off
    ENTRYPOINT: re.Pattern
    FUNCTION:   re.Pattern
    CLASS:      Optional[re.Pattern]
    IF:         re.Pattern
    ELIF:       re.Pattern
    ELSE:       re.Pattern
    CASE:       Optional[re.Pattern]
    FOR:        re.Pattern
    WHILE:      re.Pattern
    UNTIL:      Optional[re.Pattern]
    # fmt: on


class PathPatterns(TypedDict):
    """Patterns for different path types."""

    # fmt: off
    symlink: re.Pattern
    package: re.Pattern
    url:     re.Pattern
    # fmt: on


T = TypeVar("T")


class EnumValue(Protocol[T]):
    """Protocol for enum values containing patterns."""

    patterns: T


class PatternCollection(Enum):
    """Collection of regex patterns for various utilities."""

    # fmt: off
    STEP: EnumValue[StepPatterns] = {
        "any":        pattern_factory("any"),
        "output":     pattern_factory("output"),
        "comment":    pattern_factory("comment"),
    }
    BASH: EnumValue[ScriptPatterns] = {
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
    }
    PYTHON: EnumValue[ScriptPatterns] = {
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
    }
    PATH: EnumValue[PathPatterns] = {
        "symlink":    re.compile(r"^symlink://(.*)$"),
        "package":    re.compile(r"package://([^/]+)/(.*?)"),
        "url":        re.compile(r"^https?://[^\s]+$"),
    }
    # fmt: on

    @property
    def patterns(self) -> T:
        return self.value
