from typing import NotRequired, TypedDict


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
