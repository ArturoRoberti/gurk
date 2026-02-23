from pathlib import Path
from typing import TypeAlias, TypedDict

from ..remotes import GitQuery


class PluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | str
    remote:  None | GitQuery
    # fmt: on


PluginRegistry: TypeAlias = dict[str, PluginRegistryEntry]
ZippedRegistry: TypeAlias = tuple[Path, PluginRegistry]


class ResolvedPluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | Path
    remote:  None | GitQuery
    # fmt: on


ResolvedPluginRegistry: TypeAlias = dict[str, ResolvedPluginRegistryEntry]
ResolvedZippedRegistry: TypeAlias = tuple[Path, ResolvedPluginRegistry]
