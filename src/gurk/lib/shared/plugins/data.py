from typing import TypedDict

from .manifest import ResolvedPluginManifest
from .metadata import FilteredPluginMetadata
from .registry import PluginRegistryEntry


class PluginData(TypedDict):
    # fmt: off
    registration: PluginRegistryEntry
    manifest:     ResolvedPluginManifest
    metadata:     FilteredPluginMetadata
    # fmt: on
