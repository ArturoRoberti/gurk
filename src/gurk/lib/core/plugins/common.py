from enum import Enum, auto
from typing import NotRequired, TypeAlias, TypedDict

from gurk.lib.core.context.registry_manager import PluginRegistryEntry
from gurk.lib.utils.common import PathLike
from gurk.lib.utils.remotes import GitQuery
from gurk.lib.utils.tasks import (
    CustomTaskDictCollection,
    DefaultTaskDictCollection,
    ResolvedCustomTaskDictCollection,
    ResolvedDefaultTaskDictCollection,
)


#########################################################################################
#################################### Minor utilities ####################################
#########################################################################################
class FilteredPluginMetadata(TypedDict):
    # fmt: off
    name:         str
    version:      str
    description:  str
    dependencies: list[str]
    # fmt: on


class PluginMetadataDependencies(TypedDict):
    gurk: NotRequired[list[str]]


class PluginMetadata(TypedDict):
    # fmt: off
    name:                  str
    version:               str
    description:           str
    optional_dependencies: NotRequired[PluginMetadataDependencies]
    # fmt: on


# NOTE: The key "default" is required
PluginOptions: TypeAlias = dict[str, CustomTaskDictCollection]
ResolvedPluginOptions: TypeAlias = dict[str, ResolvedCustomTaskDictCollection]


class PluginManifest(TypedDict):
    # fmt: off
    imports: NotRequired[list[GitQuery | str]]
    tasks:   NotRequired[DefaultTaskDictCollection]
    options: PluginOptions
    # fmt: on


class ResolvedPluginManifest(TypedDict):
    # fmt: off
    imports: list[GitQuery | str]
    tasks:   ResolvedDefaultTaskDictCollection
    options: ResolvedPluginOptions
    # fmt: on


class PluginData(TypedDict):
    # fmt: off
    registration: PluginRegistryEntry
    manifest:     ResolvedPluginManifest
    metadata:     FilteredPluginMetadata
    # fmt: on


PluginSource: TypeAlias = PathLike | GitQuery
PluginSpecification: TypeAlias = str | PluginSource


class PluginSpecificationEnum(Enum):
    # fmt: off
    LOCAL_PATH  = auto()
    GIT_REMOTE  = auto()
    PLUGIN_NAME = auto()
    # fmt: on


GURK_MANIFEST_FILENAME = "gurk-manifest.yaml"
