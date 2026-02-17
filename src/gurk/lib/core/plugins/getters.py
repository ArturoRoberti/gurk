import shutil
import subprocess
from pathlib import Path
from typing import Iterator

from gurk.lib.context.logger import get_logger
from gurk.lib.context.registry import (
    get_available_plugin_names,
    get_plugin_registration,
)
from gurk.lib.shared.configs import load_toml, load_yaml
from gurk.lib.shared.dicts import fill_typed_dict
from gurk.lib.shared.plugins import (
    FilteredPluginMetadata,
    PluginData,
    PluginManifest,
    PluginSource,
    PluginSpecification,
    ResolvedPluginManifest,
)
from gurk.lib.shared.remotes import GitQuery, edit_url, git_clone, is_git_repo
from gurk.lib.shared.tasks import (
    ResolvedDefaultTaskDictCollection,
    TaskDictCollection,
)
from gurk.lib.utils import (
    GURK_MANIFEST_FILENAME,
    GURK_METADATA_FILENAME,
    PathLike,
    full_isinstance,
    generate_random_path,
    typecheck,
)

from .check import check_local_plugin, filter_metadata


@typecheck
def get_raw_plugin_manifest(
    plugin: PluginSpecification,
) -> PluginManifest | None:
    """
    Get the raw manifest of a plugin if it exists locally.

    :param plugin: Name, utils.PathLike, or GitQuery of the plugin
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
        plugin_registration_entry["local"] / GURK_MANIFEST_FILENAME
    )
    if raw_plugin_yaml is None:
        return None

    return raw_plugin_yaml


@typecheck
def get_resolved_plugin_manifest(
    plugin: PluginSpecification,
) -> ResolvedPluginManifest | None:
    """
    Get the manifest of a local plugin with
    - all paths resolved and converted to "Path" objects
    - missing properties filled with default values

    :param plugin: Name, utils.PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :return: Plugin configuration with resolved paths and filled properties if the plugin exists locally, None otherwise
    :rtype: ResolvedPluginManifest | None
    """
    plugin_manifest = get_raw_plugin_manifest(plugin)
    if not plugin_manifest:
        return None

    # Fill missing properties
    plugin_manifest = fill_typed_dict(plugin_manifest, ResolvedPluginManifest)

    # Expand task paths
    plugin_registration = get_plugin_registration(
        plugin, home_registry=True, package_registry=True
    )
    if not plugin_registration:
        return None
    plugin_registration_entry = next(iter(plugin_registration.values()))
    for _, task in plugin_manifest["tasks"].items():
        # Expand script path
        task["script"] = plugin_registration_entry["local"] / task["script"]

        # Expand config_file path (if applicable)
        if task["config_file"] is not None:
            task["config_file"] = (
                plugin_registration_entry["local"] / task["config_file"]
            )

    # Expand option task paths
    for _, option in plugin_manifest["options"].items():
        for _, task in option.items():
            # Expand config_file path (if applicable)
            if task["config_file"] is not None:
                task["config_file"] = (
                    plugin_registration_entry["local"] / task["config_file"]
                )

    return plugin_manifest


@typecheck
def _get_plugin_metadata(
    plugin: PluginSpecification,
) -> FilteredPluginMetadata | None:
    """
    Get the pyproject.toml metadata of a local plugin.

    :param plugin: Name, utils.PathLike, or GitQuery of the plugin
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
        plugin_registration_entry["local"] / GURK_METADATA_FILENAME
    )
    if not toml_data:
        return None

    return filter_metadata(toml_data)


@typecheck
def get_plugin_data(
    plugin: PluginSpecification,
) -> PluginData:
    """
    Get the registry entry, manifest and pyproject.toml metadata of a local plugin.

    :param plugin: Name, utils.PathLike, or GitQuery of the plugin
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
    Yields all config files of installed plugins.

    :return: Iterator of Paths to config files
    :rtype: Iterator[Path]
    """
    all_tasks = get_available_plugin_tasks()
    for task in all_tasks.values():
        if task.get("config_file"):
            yield task["config_file"]


@typecheck
def _get_relevant_files_local(
    plugin_path: PathLike, *, relative: bool = True
) -> set[Path] | None:
    """
    Get the set of relevant plugin files (script, config_file, manifest) for a plugin given its local path.

    :param plugin_path: Path to a local directory containing a plugin manifest
    :type plugin_path: PathLike
    :param relative: Whether to return paths relative to the plugin path
    :type relative: bool
    :return: Set of Paths to relevant plugin files
    :rtype: set[Path] | None
    """

    def rel_path(path_str: str) -> Path:
        return (
            Path(path_str)
            if relative
            else (Path(plugin_path) / path_str).expanduser().resolve()
        )

    plugin_manifest = Path(plugin_path) / GURK_MANIFEST_FILENAME
    if not plugin_manifest.exists():
        return None

    raw_plugin_yaml = load_yaml(plugin_manifest)
    if not raw_plugin_yaml or not full_isinstance(
        raw_plugin_yaml, PluginManifest
    ):
        return None

    # Defined tasks
    relevant_files = {
        rel_path(GURK_MANIFEST_FILENAME),
        rel_path(GURK_METADATA_FILENAME),
    }
    for task in raw_plugin_yaml.get("tasks", {}).values():
        # 'script'
        relevant_files.add(rel_path(task["script"]))
        # 'config_file' (if applicable)
        if task.get("config_file"):
            relevant_files.add(rel_path(task["config_file"]))

    # Option tasks
    for option in raw_plugin_yaml.get("options", {}).values():
        for task in option.values():
            # 'config_file' (if applicable)
            if task.get("config_file"):
                relevant_files.add(rel_path(task["config_file"]))

    return relevant_files


@typecheck
def _get_relevant_files_remote(
    plugin_remote: str | GitQuery, *, relative: bool = True
) -> set[Path] | None:
    """
    Get the set of relevant plugin files (script, config_file, manifest) for a plugin given its remote source.

    :param plugin_remote: Remote source of the plugin
    :type plugin_remote: str | GitQuery
    :param relative: Whether to return paths relative to the plugin path
    :type relative: bool
    :return: Set of Paths to relevant plugin files
    :rtype: set[Path] | None
    """
    if not is_git_repo(plugin_remote):
        return None

    # Import manifest to random file
    temp_dir = generate_random_path(prefix="gurk_plugin_", create=True)
    temp_manifest = temp_dir / GURK_MANIFEST_FILENAME
    try:
        git_clone(
            edit_url(plugin_remote, path=GURK_MANIFEST_FILENAME),
            temp_manifest,
        )
    except subprocess.CalledProcessError:
        return None

    # Determine relevant files
    relevant_files = _get_relevant_files_local(temp_dir, relative=relative)

    # Clone all relevant files to temporary directory if absolute paths are requested
    def reverse_rel_path(path: Path) -> Path:
        return path if relative else path.relative_to(temp_dir)

    if not relative and relevant_files is not None:
        for file in relevant_files:
            if file.name == GURK_MANIFEST_FILENAME:
                continue  # Manifest is already imported
            relative_file = str(reverse_rel_path(file))
            try:
                git_clone(
                    edit_url(plugin_remote, path=relative_file),
                    temp_dir / relative_file,
                )
            except subprocess.CalledProcessError as e:
                get_logger().error(
                    f"Failed to pull relevant file '{relative_file}' for plugin from its remote repository: {e}"
                )
                return None

    # Cleanup - if only relative paths are asked for, remove the temporary directory
    if relative and temp_dir.exists():
        shutil.rmtree(temp_dir)

    return relevant_files


@typecheck
def get_relevant_plugin_files(
    plugin_source: PluginSource, *, relative: bool = True
) -> set[Path] | None:
    """
    Get the set of relevant plugin files (script, config_file, manifest) for a plugin given its source.

    :param plugin_source: Source of the plugin
    :type plugin_source: PluginSource
    :param relative: Whether to return paths relative to the plugin path. If False, returns absolute paths and clones files from the remote if necessary.
    :type relative: bool
    :return: Set of Paths to relevant plugin files
    :rtype: set[Path] | None
    :raises ValueError: If the plugin source is invalid
    """
    if plugin_source.exists():
        return _get_relevant_files_local(plugin_source, relative=relative)
    elif is_git_repo(plugin_source):
        return _get_relevant_files_remote(plugin_source, relative=relative)
    else:
        raise ValueError(
            f"Invalid plugin source '{plugin_source}' - must be a git remote or a local plugin path"
        )
