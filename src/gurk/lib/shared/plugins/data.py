from typing import TypedDict

from .manifest import ResolvedPluginManifest
from .metadata import FilteredPluginMetadata
from .registry import ResolvedPluginRegistryEntry


class PluginData(TypedDict):
    # fmt: off
    registration: ResolvedPluginRegistryEntry
    manifest:     ResolvedPluginManifest
    metadata:     FilteredPluginMetadata
    # fmt: on
