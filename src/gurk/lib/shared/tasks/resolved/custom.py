from pathlib import Path
from typing import TypeAlias, TypedDict


class ResolvedCustomTaskDict(TypedDict):
    """Dictionary representing a resolved custom task configuration."""

    # fmt: off
    config_file: None | Path
    args:        list[str]
    # fmt: on


ResolvedCustomTaskDictCollection: TypeAlias = dict[str, ResolvedCustomTaskDict]
