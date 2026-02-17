from pathlib import Path
from typing import NotRequired, TypeAlias, TypedDict


class CustomTaskDict(TypedDict):
    """Dictionary representing a custom task configuration."""

    # fmt: off
    config_file: NotRequired[None | str | Path]
    args:        NotRequired[list[str]]
    # fmt: on


CustomTaskDictCollection: TypeAlias = dict[str, CustomTaskDict]
