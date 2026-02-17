from enum import Enum, auto
from typing import TypeAlias

from gurk.lib.utils import PathLike

from ..remotes import GitQuery

PluginSource: TypeAlias = PathLike | GitQuery
PluginSpecification: TypeAlias = str | PluginSource


class PluginSpecificationEnum(Enum):
    # fmt: off
    LOCAL_PATH  = auto()
    GIT_REMOTE  = auto()
    PLUGIN_NAME = auto()
    # fmt: on
