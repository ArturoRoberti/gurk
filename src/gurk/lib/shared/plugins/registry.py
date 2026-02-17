from pathlib import Path
from typing import NotRequired, TypeAlias, TypedDict

from ..remotes import GitQuery


class LocalPluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | str
    remote:  NotRequired[None | GitQuery]
    # fmt: on


class RemotePluginRegistryEntry(TypedDict):
    # fmt: off
    local:   NotRequired[None | str]
    remote:  None | GitQuery
    # fmt: on


class PluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | Path
    remote:  None | GitQuery
    # fmt: on


PluginRegistry: TypeAlias = dict[str, PluginRegistryEntry]
ZippedRegistry: TypeAlias = tuple[Path, PluginRegistry]
