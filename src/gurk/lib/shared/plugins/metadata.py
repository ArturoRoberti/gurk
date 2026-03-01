from typing import NotRequired, TypedDict


class _PluginMetadataBase(TypedDict):
    name: str
    version: str
    description: str


class ResolvedPluginMetadata(_PluginMetadataBase):
    dependencies: list[str]


class PluginMetadataDependencies(TypedDict):
    gurk: NotRequired[list[str]]


class PluginMetadataProject(_PluginMetadataBase):
    __annotations__ = {  # Syntax necessary for hyphen in dependencies
        "optional-dependencies": NotRequired[PluginMetadataDependencies],
    }


class PluginMetadata(TypedDict):
    project: PluginMetadataProject
