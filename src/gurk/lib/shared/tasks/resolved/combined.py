from typing import TypeAlias

from .custom import ResolvedCustomTaskDict
from .defined import ResolvedDefaultTaskDict


class ResolvedTaskDict(ResolvedDefaultTaskDict, ResolvedCustomTaskDict):
    """Dictionary representing a full resolved task configuration."""

    pass


ResolvedTaskDictCollection: TypeAlias = dict[str, ResolvedTaskDict]
