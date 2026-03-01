from typing import TypeAlias

from .custom import CustomTaskDict
from .defined import DefaultTaskDict


class TaskDict(DefaultTaskDict, CustomTaskDict):
    """Dictionary representing a full task configuration."""

    pass


TaskDictCollection: TypeAlias = dict[str, TaskDict]
