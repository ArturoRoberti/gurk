from pathlib import Path
from typing import Iterator

from gurk.lib.core.context.registry_manager import (
    get_available_plugin_names,
    get_plugin_registration,
)
from gurk.lib.utils.configs import load_toml, load_yaml
from gurk.lib.utils.tasks import (
    ResolvedDefaultTaskDictCollection,
    TaskDictCollection,
)
from gurk.lib.utils.typed_dict import fill_typed_dict

from .check import check_local_plugin, filter_metadata
from .common import (
    GURK_MANIFEST_FILENAME,
    FilteredPluginMetadata,
    PluginData,
    PluginManifest,
    PluginSpecification,
    ResolvedPluginManifest,
)


def get_raw_plugin_manifest(
    plugin: PluginSpecification,
) -> PluginManifest | None:
    """
    Get the raw manifest of a plugin if it exists locally.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :return: Plugin manifest if the plugin exists locally, None otherwise
    :rtype: PluginManifest | None
    """
    plugin_registration = get_plugin_registration(
        plugin, home_registry=True, package_registry=True
    )
    if not plugin_registration:
        return None
    plugin_registration_entry = next(iter(plugin_registration.values()))

    if not check_local_plugin(plugin_registration_entry["local"]):
        return None

    raw_plugin_yaml = load_yaml(
        Path(plugin_registration_entry["local"]) / GURK_MANIFEST_FILENAME
    )
    if raw_plugin_yaml is None:
        return None

    return raw_plugin_yaml


def get_resolved_plugin_manifest(
    plugin: PluginSpecification,
) -> ResolvedPluginManifest | None:
    """
    Get the manifest of a local plugin with
    - all paths resolved and converted to "Path" objects
    - missing properties filled with default values

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :return: Plugin configuration with resolved paths and filled properties if the plugin exists locally, None otherwise
    :rtype: ResolvedPluginManifest | None
    """
    plugin_manifest = get_raw_plugin_manifest(plugin)
    if not plugin_manifest:
        return None

    # Fill missing properties
    plugin_manifest: ResolvedPluginManifest = fill_typed_dict(
        plugin_manifest, ResolvedPluginManifest
    )

    # Expand task paths
    plugin_registration = get_plugin_registration(
        plugin, home_registry=True, package_registry=True
    )
    if not plugin_registration:
        return None
    plugin_registration_entry = next(iter(plugin_registration.values()))
    plugin_path = Path(plugin_registration_entry["local"])
    for _, task in plugin_manifest["tasks"].items():
        # Expand script path
        task["script"] = plugin_path / task["script"]

        # Expand config_file path (if applicable)
        if task["config_file"] is not None:
            task["config_file"] = plugin_path / task["config_file"]

    # Expand option task paths
    for _, option in plugin_manifest["options"].items():
        for _, task in option.items():
            # Expand config_file path (if applicable)
            if task["config_file"] is not None:
                task["config_file"] = plugin_path / task["config_file"]

    return plugin_manifest


def _get_plugin_metadata(
    plugin: PluginSpecification,
) -> FilteredPluginMetadata | None:
    """
    Get the pyproject.toml metadata of a local plugin.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :return: Plugin metadata if the plugin exists locally, None otherwise
    :rtype: FilteredPluginMetadata | None
    """
    plugin_registration = get_plugin_registration(
        plugin, home_registry=True, package_registry=True
    )
    if not plugin_registration:
        return None
    plugin_registration_entry = next(iter(plugin_registration.values()))

    if not check_local_plugin(plugin_registration_entry["local"]):
        return None

    toml_data = load_toml(
        Path(plugin_registration_entry["local"]) / "pyproject.toml"
    )
    if not toml_data:
        return None

    return filter_metadata(toml_data)


def get_plugin_data(plugin: PluginSpecification) -> PluginData:
    """
    Get the registry entry, manifest and pyproject.toml metadata of a local plugin.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :return: Plugin data containing registry entry, manifest and metadata
    :rtype: PluginData
    :raises ModuleNotFoundError: If no valid plugin was found
    """

    def error_msg(message: str) -> str:
        return f"ERROR loading plugin data for {plugin}: {message}"

    plugin_registration = get_plugin_registration(
        plugin, home_registry=True, package_registry=True
    )
    if not plugin_registration:
        raise ModuleNotFoundError(
            error_msg("Could not load a (valid) plugin entry")
        )

    plugin_manifest = get_resolved_plugin_manifest(plugin)
    if not plugin_manifest:
        raise ModuleNotFoundError(
            error_msg(
                f"Could not load a (valid) {GURK_MANIFEST_FILENAME} file"
            )
        )

    plugin_metadata = _get_plugin_metadata(plugin)
    if not plugin_metadata:
        raise ModuleNotFoundError(
            error_msg(
                "UNEXPECTED: Could not load plugin metadata from a (valid) pyproject.toml file"
            )
        )

    return PluginData(
        registration=next(iter(plugin_registration.values())),
        manifest=plugin_manifest,
        metadata=plugin_metadata,
    )


def get_available_plugin_tasks() -> ResolvedDefaultTaskDictCollection:
    """
    Get the combined task definitions of all local plugins.

    :return: Dictionary of tasks from all local plugins
    :rtype: ResolvedDefaultTaskDictCollection
    """
    combined_tasks: TaskDictCollection = {}
    for plugin in get_available_plugin_names():
        plugin_manifest = get_resolved_plugin_manifest(plugin)
        if plugin_manifest:
            combined_tasks.update(plugin_manifest["tasks"])

    return combined_tasks


def iter_scripts() -> Iterator[Path]:
    """
    Yields all script files of installed plugins.

    :return: Iterator of Paths to script files
    :rtype: Iterator[Path]
    """
    all_tasks = get_available_plugin_tasks()
    for task in all_tasks.values():
        yield task["script"]


def iter_configs() -> Iterator[Path]:
    """
    Yields all script files of installed plugins.

    :return: Iterator of Paths to script files
    :rtype: Iterator[Path]
    """
    all_tasks = get_available_plugin_tasks()
    for task in all_tasks.values():
        if task.get("config_file"):
            yield task["config_file"]
