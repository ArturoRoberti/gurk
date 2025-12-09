import re
from enum import Enum
from typing import Optional, Protocol, TypedDict, TypeVar

T = TypeVar("T")


class ScriptBlockPatterns(TypedDict):
    # fmt: off
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


class PatternFactory(Protocol):
    def __call__(self, *, progress: bool) -> re.Pattern:
        ...


def pattern_factory(base_type: str) -> PatternFactory:
    """
    base_type: 'any', 'output', or 'comment'
    """

    def factory(*, progress: bool) -> re.Pattern:
        step_type = "STEP"
        if not progress:
            step_type += "_NO_PROGRESS"

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
    # fmt: off
    any:     PatternFactory
    output:  PatternFactory
    comment: PatternFactory
    # fmt: on


class ScriptPatterns(TypedDict):
    # fmt: off
    entrypoints: Optional[re.Pattern]
    blocks:      ScriptBlockPatterns
    # fmt: on


class PathPatterns(TypedDict):
    # fmt: off
    path:    re.Pattern
    link:    re.Pattern
    package: re.Pattern
    url:     re.Pattern
    # fmt: on


class EnumValue(Protocol[T]):
    patterns: T


class PatternCollection(Enum):
    # fmt: off
    STEP: EnumValue[StepPatterns] = {
        "any":          pattern_factory("any"),
        "output":       pattern_factory("output"),
        "comment":      pattern_factory("comment"),
    }
    BASH: EnumValue[ScriptPatterns] = {
        "entrypoints":  re.compile(r"if\s+\[\[.*BASH_SOURCE.*\]\];?\s*"),
        "blocks": {
            "FUNCTION": re.compile(r"\s*(?:function\s+|)(\w+)\s*\(\)\s*{\s*$"),
            "CLASS":    None,  # Bash has no classes
            "IF":       re.compile(r"^\s*if\s+(.*);\s*then\s*$"),
            "ELIF":     re.compile(r"^\s*elif\s+(.*);\s*then\s*$"),
            "ELSE":     re.compile(r"^\s*else\s*$"),
            "CASE":     re.compile(r"^\s*case\s+(.*)\s*in\s*$"),
            "FOR":      re.compile(r"^\s*for\s+(.*);\s*do\s*$"),
            "WHILE":    re.compile(r"^\s*while\s+(.*);\s*do\s*$"),
            "UNTIL":    re.compile(r"^\s*until\s+(.*);\s*do\s*$"),
        },
    }
    PYTHON: EnumValue[ScriptPatterns] = {
        "entrypoints":  re.compile(r'if __name__\s*==\s*[\'"]__main__[\'"]\s*:'),
        "blocks": {
            "FUNCTION": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*:\s*$"),
            "CLASS":    re.compile(r"^\s*class\s+(\w+)\s*(\(.*\))?:\s*$"),
            "IF":       re.compile(r"^\s*if\s+(.*):\s*$"),
            "ELIF":     re.compile(r"^\s*elif\s+(.*):\s*$"),
            "ELSE":     re.compile(r"^\s*else\s*:\s*$"),
            "CASE":     None,  # Python has no "case"
            "FOR":      re.compile(r"^\s*for\s+(.*):\s*$"),
            "WHILE":    re.compile(r"^\s*while\s+(.*):\s*$"),
            "UNTIL":    None,  # Python has no "until"
        },
    }
    PATH: EnumValue[PathPatterns] = {
        "path":         re.compile(r"^package://(.*)$"),
        "link":         re.compile(r"^link://(.*)$"),
        "package":      re.compile(r"^package://([^/]+)/(.*)$"),
        "url":          re.compile(r"^https?://[^\s]+$"),
    }
    # fmt: on

    @property
    def patterns(self) -> T:
        return self.value
