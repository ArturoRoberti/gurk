from pathlib import Path
from typing import TypeAlias, TypedDict

from .args import ResolvedArgsDefinitionCollection


class ResolvedDefaultTaskDict(TypedDict):
    """Dictionary representing a resolved default task configuration."""

    # fmt: off
    description:    str
    script:         Path
    function:       None | str
    config_file:    None | Path
    depends_on:     list[str]
    privileged:     bool
    supercedes:     list[str]
    args:           ResolvedArgsDefinitionCollection
    # fmt: on


ResolvedDefaultTaskDictCollection: TypeAlias = dict[
    str, ResolvedDefaultTaskDict
]
