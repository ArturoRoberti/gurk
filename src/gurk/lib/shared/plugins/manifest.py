from typing import NotRequired, TypeAlias, TypedDict

from ..remotes import GitQuery
from ..tasks import (
    CustomTaskDictCollection,
    DefaultTaskDictCollection,
    ResolvedCustomTaskDictCollection,
    ResolvedDefaultTaskDictCollection,
)

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
