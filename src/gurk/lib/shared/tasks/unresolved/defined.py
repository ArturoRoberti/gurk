from typing import NotRequired, TypeAlias, TypedDict

from .args import ArgsDefinitionCollection


class DefaultTaskDict(TypedDict):
    """Dictionary representing a default task configuration."""

    # fmt: off
    description:    str
    script:         str
    function:       None | str
    config_file:    NotRequired[None | str]
    depends_on:     NotRequired[list[str]]
    privileged:     NotRequired[bool]
    supercedes:     NotRequired[list[str]]
    args:           NotRequired[ArgsDefinitionCollection]
    # fmt: on


DefaultTaskDictCollection: TypeAlias = dict[str, DefaultTaskDict]
