from typing import TypeAlias, TypedDict, Union


class ResolvedArgsDefinition(TypedDict):
    """Dictionary representing argument definitions for tasks."""

    # fmt: off
    help:        str
    default:     None | bool | str | list[str]
    choices:     None | list[str]
    nargs:       None | Union[int, str]
    mutex:       None | str
    # fmt: on


ResolvedArgsDefinitionCollection: TypeAlias = dict[str, ResolvedArgsDefinition]
