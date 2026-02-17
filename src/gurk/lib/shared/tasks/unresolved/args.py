from typing import NotRequired, TypeAlias, TypedDict, Union


class ArgsDefinition(TypedDict):
    """Dictionary representing argument definitions for tasks."""

    # fmt: off
    help:        str
    default:     NotRequired[None | bool | str | list[str]]
    choices:     NotRequired[None | list[str]]
    nargs:       NotRequired[None | Union[int, str]]
    mutex:       NotRequired[None | str]
    # fmt: on


ArgsDefinitionCollection: TypeAlias = dict[str, ArgsDefinition]
