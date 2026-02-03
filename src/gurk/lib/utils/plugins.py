import json
import os
import re
import shutil
import subprocess
import venv
from argparse import (
    SUPPRESS,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    ArgumentTypeError,
    Namespace,
    _ArgumentGroup,
)
from collections import defaultdict
from pathlib import Path
from typing import Iterator, NotRequired, Sequence, TypeAlias, TypedDict

import networkx as nx

from gurk.lib.logger import get_logger
from gurk.lib.utils.common import (
    PACKAGE_HOME_PATH,
    PACKAGE_SRC_PATH,
    PACKAGE_VENVS_PATH,
    YES_ANSWERS,
    PathLike,
    check_version,
    generate_random_path,
)
from gurk.lib.utils.configs import dump_yaml, load_toml, load_yaml
from gurk.lib.utils.remotes import (
    GitRef,
    edit_url,
    extract_url,
    git_clone,
    is_git_repo,
)
from gurk.lib.utils.scripts import (
    ScriptBlockTypes,
    check_script_blocks,
    get_block_spans,
)
from gurk.lib.utils.system_info import SystemInfo
from gurk.lib.utils.tasks import (
    ArgsDefinition,
    ArgsDefinitionCollection,
    CustomTaskDictCollection,
    DefaultTaskDictCollection,
    ResolvedCustomTaskDictCollection,
    ResolvedDefaultTaskDictCollection,
    TaskDictCollection,
)
from gurk.lib.utils.typed_dict import (
    fill_typed_dict,
    print_typed_dict_types,
    validate_typed_dict,
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

    @staticmethod
    def filtered(metadata: dict) -> FilteredPluginMetadata | None:
        """
        Return a filtered version of the PluginMetadata containing only relevant fields.

        :param metadata: Raw pyproject.toml metadata dictionary
        :type metadata: dict
        :return: Filtered PluginMetadata
        :rtype: FilteredPluginMetadata
        """
        if not isinstance(metadata, dict):
            return None

        # 'Project' section
        project_data = metadata.get("project")
        if not project_data or not isinstance(project_data, dict):
            return None

        # Allow other fields, thus filter them out before validating
        filtered_metadata = {
            k.replace("-", "_"): v
            for k, v in project_data.items()
            if k.replace("-", "_") in PluginMetadata.__annotations__
        }
        filtered_metadata["optional_dependencies"] = {
            k: v
            for k, v in project_data.get("optional-dependencies", {}).items()
            if k in PluginMetadataDependencies.__annotations__
        }

        # Validate structure
        if not validate_typed_dict(filtered_metadata, PluginMetadata):
            return None

        # Version
        if not check_version(filtered_metadata["version"]):
            return None

        # Dependencies
        optional_deps = filtered_metadata.pop("optional_dependencies", {})
        filtered_metadata["dependencies"] = optional_deps.get("gurk", [])

        return filtered_metadata


# NOTE: The key "default" is required
PluginOptions: TypeAlias = dict[str, CustomTaskDictCollection]
ResolvedPluginOptions: TypeAlias = dict[str, ResolvedCustomTaskDictCollection]


class PluginManifest(TypedDict):
    # fmt: off
    imports: NotRequired[list[GitRef | str]]
    tasks:   NotRequired[DefaultTaskDictCollection]
    options: PluginOptions
    # fmt: on


class ResolvedPluginManifest(TypedDict):
    # fmt: off
    imports: list[GitRef | str]
    tasks:   ResolvedDefaultTaskDictCollection
    options: ResolvedPluginOptions
    # fmt: on


class PluginRegistryEntry(TypedDict):
    # fmt: off
    local:   str | None
    remote:  GitRef | None
    # fmt: on


class PluginData(TypedDict):
    # fmt: off
    registration: PluginRegistryEntry
    manifest:     ResolvedPluginManifest
    metadata:     FilteredPluginMetadata
    # fmt: on


PluginSpec: TypeAlias = str | PathLike | GitRef

GURK_MANIFEST_FILENAME = "gurk-manifest.yaml"


def _get_plugin_dirs(
    home_registry: bool = True, package_registry: bool = True
) -> tuple[Path, ...]:
    """
    Get a tuple of plugin directories, with the home one first.

    :param home_registry: Whether to include the home plugin directory
    :type home_registry: bool
    :param package_registry: Whether to include the package plugin directory
    :type package_registry: bool
    :return: Tuple of plugin directories (home, package), depending on the input
    :rtype: tuple[Path, ...]
    """
    parent_paths: list[Path] = []
    if home_registry:
        parent_paths.append(PACKAGE_HOME_PATH)
    if package_registry:
        parent_paths.append(PACKAGE_SRC_PATH)

    possible_plugin_paths = [p / "plugins" for p in parent_paths]
    for p in possible_plugin_paths:
        p.mkdir(parents=True, exist_ok=True)

    return tuple(possible_plugin_paths)


def _get_plugin_registries(
    home_registry: bool = True, package_registry: bool = True
) -> tuple[Path, ...]:
    """
    Get a tuple of plugin registries, with the home one first.

    :param home_registry: Whether to include the home plugin registry
    :type home_registry: bool
    :param package_registry: Whether to include the package plugin registry
    :type package_registry: bool
    :return: Tuple of plugin registries (home, package), depending on the input
    :rtype: tuple[Path, ...]
    """
    possible_plugin_registries = [
        p / "registry.yaml"
        for p in _get_plugin_dirs(home_registry, package_registry)
    ]
    for p in possible_plugin_registries:
        p.touch(exist_ok=True)

    return tuple(possible_plugin_registries)


def get_combined_plugin_registry() -> dict[str, PluginRegistryEntry]:
    """
    Get the combined plugin registry from home and package registries.

    :return: Combined plugin registry
    :rtype: dict[str, PluginRegistryEntry]
    """
    home_registry_file, package_registry_file = _get_plugin_registries()

    # Get home registry and prepend path to 'local' entries
    home_registry = load_yaml(home_registry_file) or {}
    for entry in home_registry.values():
        entry["local"] = (
            str(Path(home_registry_file).parent / entry["local"])
            if entry["local"]
            else entry["local"]
        )

    # Get package registry and prepend path to 'local' entries
    package_registry = load_yaml(package_registry_file) or {}
    for entry in package_registry.values():
        entry["local"] = (
            str(Path(package_registry_file).parent / entry["local"])
            if entry["local"]
            else entry["local"]
        )

    # Combine registries, prioritizing home registry
    combined_registry = package_registry.copy()
    combined_registry.update(home_registry)

    # Remove the template plugin
    del combined_registry["template"]

    return combined_registry


def _get_possible_plugin_entries(
    plugin: PluginSpec,
    home_registry: bool = True,
    package_registry: bool = True,
    require_local: bool = True,
) -> tuple[tuple[str | None, PluginRegistryEntry | None], ...]:
    """
    Get possible plugin registry entries for a given plugin name.
        NOTE: This does not check the validity of the plugin yaml file.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :param home_registry: Whether to check the home plugin registry
    :type home_registry: bool
    :param package_registry: Whether to check the package plugin registry
    :type package_registry: bool
    :param require_local: Whether to only return entries with a local path
    :type require_local: bool
    :return: Tuple of possible PluginRegistryEntry objects for the plugin, or None if not found
    :rtype: tuple[tuple[str | None, PluginRegistryEntry | None], ...]
    """
    plugin = str(plugin)

    def _load_plugin(
        registry_file: Path,
    ) -> tuple[str | None, PluginRegistryEntry | None]:
        registry: dict[str, PluginRegistryEntry] = (
            load_yaml(registry_file) or {}
        )

        # Get plugin entry
        name_via_remote = next(
            (
                k
                for k, v in registry.items()
                if v.get("remote")
                and extract_url(plugin) == extract_url(v["remote"])
            ),
            None,
        )
        name_via_local = next(
            (
                k
                for k, v in registry.items()
                if v.get("local")
                and registry_file.parent / v["local"]
                == registry_file.parent / Path(plugin).expanduser()
            ),
            None,
        )
        if plugin in registry:
            # Access plugin by name
            name = plugin
        elif name_via_remote:
            # Access plugin by remote
            name = name_via_remote
        elif name_via_local:
            # Access plugin by local path
            name = name_via_local
        else:
            # Plugin not found
            return None, None
        entry = registry[name]

        # Validate structure
        if not validate_typed_dict(entry, PluginRegistryEntry):
            return None, None

        # Validate that it has a local path
        if require_local and not entry["local"]:
            return None, None

        # Resolve local path
        if entry["local"] is not None:
            local_path = registry_file.parent / entry["local"]
            if (
                not local_path.is_dir()
                or not (local_path / GURK_MANIFEST_FILENAME).is_file()
            ):
                return None, None
            entry["local"] = str(local_path)

        return name, entry

    plugin_registries = _get_plugin_registries(home_registry, package_registry)
    plugin_entries = []
    for registry_file in plugin_registries:
        name, entry = _load_plugin(registry_file)
        if name and entry:
            plugin_entries.append((name, entry))

    return tuple(plugin_entries)


def _get_plugin_registration(
    plugin: PluginSpec,
    home_registry: bool = True,
    package_registry: bool = True,
    require_local: bool = True,
) -> tuple[str | None, PluginRegistryEntry | None]:
    """
    Get the registry entry of a plugin (path, remote) if it exists locally.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :param home_registry: Whether to check the home plugin registry
    :type home_registry: bool
    :param package_registry: Whether to check the package plugin registry
    :type package_registry: bool
    :param require_local: Whether to only return entries with a local path
    :type require_local: bool
    :return: Registry entry if the plugin exists locally, None otherwise
    :rtype: tuple[str | None, PluginRegistryEntry | None]
    """
    possible_plugin_entries = _get_possible_plugin_entries(
        plugin, home_registry, package_registry, require_local
    )
    plugin_entries = tuple(p for p in possible_plugin_entries if all(p))

    # Logging
    logger = get_logger()
    if not plugin_entries:
        return (None, None)
    elif len(plugin_entries) > 1:
        logger.debug(
            f"WARNING: Multiple registry entries found for plugin '{plugin}'. Using the home one."
        )

    return plugin_entries[0]


def plugin_exists_locally(plugin: PluginSpec) -> bool:
    """
    Check if a plugin exists in the possible local plugin paths.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: True if the plugin exists locally, False otherwise
    :rtype: bool
    """
    return all(_get_plugin_registration(plugin, require_local=True))


def plugin_exists_remotely(plugin: GitRef) -> bool:
    """
    Check if a plugin exists in the possible remote plugin paths.

    :param plugin: GitRef of the plugin
    :type plugin: GitRef
    :return: True if the plugin exists remotely, False otherwise
    :rtype: bool
    """
    return is_git_repo(str(plugin))


def plugin_exists(plugin: PluginSpec) -> bool:
    """
    Check if a plugin exists either locally or remotely.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: True if the plugin exists, False otherwise
    :rtype: bool
    """
    return plugin_exists_locally(plugin) or plugin_exists_remotely(plugin)


def load_raw_plugin_manifest(plugin: PluginSpec) -> PluginManifest | None:
    """
    Get the raw manifest of a plugin if it exists locally.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: Plugin manifest if the plugin exists locally, None otherwise
    :rtype: PluginManifest | None
    """
    plugin_name, plugin_registration = _get_plugin_registration(plugin)
    if not (plugin_name and plugin_registration):
        return None

    if not check_local_plugin(plugin_registration["local"]):
        return None

    raw_plugin_yaml = load_yaml(
        Path(plugin_registration["local"]) / GURK_MANIFEST_FILENAME
    )
    if raw_plugin_yaml is None:
        return None

    return raw_plugin_yaml


def _load_resolved_plugin_manifest(
    plugin: PluginSpec,
) -> ResolvedPluginManifest | None:
    """
    Get the manifest of a local plugin with
    - all paths resolved and converted to "Path" objects
    - missing properties filled with default values

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: Plugin configuration with resolved paths and filled properties if the plugin exists locally, None otherwise
    :rtype: ResolvedPluginManifest | None
    """
    plugin_manifest = load_raw_plugin_manifest(plugin)
    if not plugin_manifest:
        return None

    # Fill missing properties
    plugin_manifest: PluginManifest = fill_typed_dict(
        plugin_manifest, PluginManifest
    )

    # Expand task paths
    _, plugin_registration = _get_plugin_registration(plugin)
    plugin_path = Path(plugin_registration["local"])
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


def _load_plugin_metadata(plugin: PluginSpec) -> FilteredPluginMetadata | None:
    """
    Get the pyproject.toml metadata of a local plugin.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: Plugin metadata if the plugin exists locally, None otherwise
    :rtype: FilteredPluginMetadata | None
    """
    plugin_name, plugin_registration = _get_plugin_registration(plugin)
    if not (plugin_name and plugin_registration):
        return None

    if not check_local_plugin(plugin_registration["local"]):
        return None

    toml_data = load_toml(
        Path(plugin_registration["local"]) / "pyproject.toml"
    )
    if not toml_data:
        return None

    return PluginMetadata.filtered(toml_data)


def get_plugin_data(plugin: PluginSpec) -> PluginData:
    """
    Get the registry entry, manifest and pyproject.toml metadata of a local plugin.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: Plugin data containing registry entry, manifest and metadata
    :rtype: PluginData
    :raises ModuleNotFoundError: If no valid plugin was found
    """

    def error_msg(message: str) -> str:
        return f"ERROR loading plugin data for {plugin}: {message}"

    plugin_name, plugin_registration = _get_plugin_registration(plugin)
    if not (plugin_name and plugin_registration):
        raise ModuleNotFoundError(
            error_msg("Could not load a (valid) plugin entry")
        )

    plugin_manifest = _load_resolved_plugin_manifest(plugin)
    if not plugin_manifest:
        raise ModuleNotFoundError(
            error_msg(
                f"Could not load a (valid) {GURK_MANIFEST_FILENAME} file"
            )
        )

    plugin_metadata = _load_plugin_metadata(plugin)
    if not plugin_metadata:
        raise ModuleNotFoundError(
            error_msg(
                "UNEXPECTED: Could not load plugin metadata from a (valid) pyproject.toml file"
            )
        )

    return PluginData(
        registration=plugin_registration,
        manifest=plugin_manifest,
        metadata=plugin_metadata,
    )


def installed_plugin_path(plugin: PluginSpec) -> Path | None:
    """
    Get the local path of a plugin if it is installed.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: Local path of the plugin if it exists locally, None otherwise
    :rtype: Path | None
    """
    plugin_registration = _get_plugin_registration(plugin)
    return (
        plugin_registration[1]["local"] if all(plugin_registration) else None
    )


def get_available_plugin_names() -> list[str]:
    """
    Get the names of all available local plugins.

    :return: List of available local plugin names
    :rtype: list[str]
    """
    combined_registry = get_combined_plugin_registry()
    return list(combined_registry.keys())


def get_combined_plugin_tasks() -> ResolvedDefaultTaskDictCollection:
    """
    Get the combined task definitions of all local plugins.

    :return: Dictionary of tasks from all local plugins
    :rtype: ResolvedDefaultTaskDictCollection
    """
    combined_tasks: TaskDictCollection = {}
    for plugin in get_available_plugin_names():
        plugin_manifest = _load_resolved_plugin_manifest(plugin)
        if plugin_manifest:
            combined_tasks.update(plugin_manifest["tasks"])

    return combined_tasks


def iter_scripts() -> Iterator[Path]:
    """
    Yields all script files of installed plugins.

    :return: Iterator of Paths to script files
    :rtype: Iterator[Path]
    """
    all_tasks = get_combined_plugin_tasks()
    for task in all_tasks.values():
        yield task["script"]


def iter_configs() -> Iterator[Path]:
    """
    Yields all script files of installed plugins.

    :return: Iterator of Paths to script files
    :rtype: Iterator[Path]
    """
    all_tasks = get_combined_plugin_tasks()
    for task in all_tasks.values():
        if task.get("config_file"):
            yield task["config_file"]


def get_local_plugin_version(plugin_path: PathLike) -> str | None:
    """
    Return the version string from the pyproject.toml file in a local repository path, or None if not found.
        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param plugin_path: Path to the local repository
    :type plugin_path: PathLike
    :return: Version string, or None if not found
    :rtype: str | None
    """
    try:
        version = load_toml(Path(plugin_path) / "pyproject.toml")["project"][
            "version"
        ]
        if not check_version(version):
            raise ValueError
        return version
    except Exception:
        return None


def add_plugin_entry(
    plugin_name: str, plugins_entry: PluginRegistryEntry
) -> bool:
    """
    Add a plugin to the home plugin registry.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :param plugins_entry: Plugin registry entry
    :type plugins_entry: PluginRegistryEntry
    :return: True if the plugin was added successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check if the plugin already exists
    _, plugin_registration = _get_plugin_registration(plugin_name)
    if plugin_registration:
        logger.error(
            f"Plugin '{plugin_name}' already exists in some registry."
        )
        return False

    # Load home plugin registry
    registry_file = _get_plugin_registries(package_registry=False)[0]
    registry: dict[str, PluginRegistryEntry] = load_yaml(registry_file) or {}

    # Add plugin entry
    registry[plugin_name] = {
        "local": plugins_entry["local"],
        "remote": plugins_entry["remote"],
    }
    dump_yaml(registry, registry_file)

    return True


def update_plugin_entry(
    plugin_name: str, local: str | None = None, remote: GitRef | None = None
) -> bool:
    """
    Update a plugin entry in any of the plugin registries.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :param local: New local path of the plugin
    :type local: str | None
    :param remote: New remote GitRef of the plugin
    :type remote: GitRef | None
    :return: True if the plugin was updated successfully, False otherwise
    :rtype: bool
    :raises ValueError: If neither local nor remote is provided
    """
    # Check args
    if local is None and remote is None:
        raise ValueError(
            "At least one of 'local' or 'remote' must be provided"
        )

    # Load registry files and update entry
    registry_files = _get_plugin_registries()
    for registry_file in registry_files:
        registry: dict[str, PluginRegistryEntry] = (
            load_yaml(registry_file) or {}
        )

        # Check if plugin exists
        if plugin_name not in registry:
            continue

        # Update plugin entry
        if local is not None:
            registry[plugin_name]["local"] = local
        if remote is not None:
            registry[plugin_name]["remote"] = remote

        # Save registry
        dump_yaml(registry, registry_file)

        return True

    return False


def _remove_plugin_entry(plugin: PluginSpec, purge: bool = False) -> None:
    """
    Remove a plugin from the home plugin registry.

    :param plugin: Name, PathLike, or GitRef of the plugin
    :type plugin: PluginSpec
    :param purge: Whether to also remove the plugin registry entry fully. Does not affect package registry entries.
    :type purge: bool
    :raises ModuleNotFoundError: If no such local plugin is found
    """
    # Check if the plugin exists
    plugin_name, plugin_registration = _get_plugin_registration(
        plugin, require_local=False
    )
    if not (plugin_name and plugin_registration):
        raise ModuleNotFoundError(
            f"Could not find plugin '{plugin}' in any registry."
        )

    # Remove plugin entries
    def _remove_single_plugin_entry(
        registry_file: Path, allow_purge: bool = False
    ) -> None:
        """
        Remove a plugin entry from a specific registry file.

        :param registry_file: Path to the registry file
        :type registry_file: Path
        :param allow_purge: Whether purging is allowed for this registry
        :type allow_purge: bool
        """
        # Get registry
        registry: dict[str, PluginRegistryEntry] = (
            load_yaml(registry_file) or {}
        )

        # Edit entry
        if purge and allow_purge:
            # Remove whole entry
            if plugin_name in registry:
                del registry[plugin_name]
        else:
            # Set local path to None
            if plugin_name in registry:
                registry[plugin_name]["local"] = None

        # Save registry
        dump_yaml(registry, registry_file)

    for registry_file, allow_purge in zip(
        _get_plugin_registries(),
        [True, False],
    ):
        _remove_single_plugin_entry(registry_file, allow_purge)


def _create_wildcard_validator(patterns: list[str]) -> tuple:
    """
    Create a validator function for wildcard patterns.

    :param patterns: List of wildcard patterns to validate against
    :type patterns: list[str]
    :return: A tuple containing a validator function and a metavar string
    :rtype: tuple
    :raises ArgumentTypeError: If validation fails
    """
    regexes = [
        re.compile("^" + re.escape(p).replace(r"\*", ".*") + "$")
        for p in patterns
    ]

    quoted = ", ".join(f"'{p}'" for p in patterns)
    metavar = "{" + ",".join(patterns) + "}"

    def validate(value: str) -> str:
        if any(rx.match(value) for rx in regexes):
            return value
        raise ArgumentTypeError(
            f"invalid choice: {value!r} (choose from {quoted})"
        )

    return validate, metavar


def check_args_dict(args_dict: ArgsDefinitionCollection) -> None:
    """
    Extend the parser with arguments defined in a plugin.

    :param args_dict: Dictionary of argument definitions
    :type args_dict: ArgsDefinitionCollection
    :raises ArgumentTypeError: If argument definitions are invalid
    """
    # Validate structure
    if not (
        isinstance(args_dict, dict)
        and all(isinstance(key, str) for key in args_dict.keys())
        and all(
            validate_typed_dict(arg_spec, ArgsDefinition)
            for arg_spec in args_dict.values()
        )
    ):
        raise ArgumentTypeError("Invalid argument definitions structure")

    # Validate mutually exclusive groups
    mutex_groups = defaultdict(list)
    for name, spec in args_dict.items():
        mutex = spec.get("mutex")
        if mutex:
            mutex_groups[mutex].append(name)
    for members in mutex_groups.values():
        if len(members) < 2:
            raise ArgumentTypeError(
                "Mutually exclusive group must have at least two members"
            )

    # Validate arguments
    for name, spec in args_dict.items():
        # nargs
        nargs = spec.get("nargs")
        if nargs and not (isinstance(nargs, int) or nargs in ("?", "*", "+")):
            raise ArgumentTypeError(
                f"Invalid nargs value for argument '{name}'"
            )

        # Boolean flags - Validate nothing else is set
        default = spec.get("default")
        if isinstance(default, bool) and any(
            k not in ("help", "default", "mutex")
            for k, v in spec.items()
            if v is not None
        ):
            raise ArgumentTypeError(
                f"Invalid boolean flag argument definition for '{name}'"
            )

        # choices
        choices = spec.get("choices")
        if choices is not None:
            # Validate choices structure
            if (
                not isinstance(choices, list)
                or not choices
                or not all(isinstance(c, str) for c in choices)
            ):
                raise ArgumentTypeError(
                    f"Invalid choices structure for argument '{name}'"
                )

            # Validate default(s) against choices
            if default is not None:
                if not isinstance(default, list):
                    default = [default]

                # Validate default structure
                if not default or not all(isinstance(d, str) for d in default):
                    raise ArgumentTypeError(
                        f"Invalid default structure for argument '{name}'"
                    )

                # Validate that all defaults are in choices
                validator, _ = _create_wildcard_validator(choices)
                for d in default:
                    try:
                        validator(d)
                    except ArgumentTypeError:
                        raise ArgumentTypeError(
                            f"Default value {d!r} for argument '{name}' is not in choices"
                        )

            # Validate nargs if no default is given
            elif nargs in ("?", "*"):
                raise ArgumentTypeError(
                    f"Invalid nargs value for argument '{name}' when no default is given"
                )


class CleanHelpFormatter(ArgumentDefaultsHelpFormatter):
    """
    Custom formatter that:
      - hides default=None and default=False for boolean flags
      - annotates mutually exclusive args automatically
      - respects max_help_position
    """

    def __init__(self, prog):
        super().__init__(prog, max_help_position=80)

    def _get_help_string(self, action):
        if action.default not in (None, SUPPRESS):
            # A default is specified and is not purposefully suppressed
            # NOTE: Inludes boolean flags ("store_true"/"store_false")
            default_suffix = f"(default: {action.default!s})"
            if not action.help:
                return default_suffix
            else:
                return action.help + " " + default_suffix
        else:
            # No default specified or default is purposefully suppressed
            return action.help or ""


class GurkArgumentParser(ArgumentParser):
    """
    Custom ArgumentParser that uses CleanHelpFormatter and adds common gurk CLI options.
    """

    def __init__(
        self,
        add_verbose_arg: bool = True,
        add_non_interactive_arg: bool = True,
        add_force_arg: bool = False,
        add_task_args: bool = False,
        allow_complex_types: bool = True,
        *args,
        **kwargs,
    ):
        # Some gurk internal variables
        self.required_group_title = "required arguments"
        self.add_non_interactive_arg = add_non_interactive_arg
        self.allow_complex_types = allow_complex_types

        # Use CleanHelpFormatter
        kwargs["formatter_class"] = lambda prog: CleanHelpFormatter(prog)

        # Call super init
        super().__init__(*args, **kwargs)

        # Add logger options
        if add_verbose_arg:
            self.add_argument(
                "-v",
                "--verbose",
                action="store_true",
                help="Enable verbose output",
            )
        if add_non_interactive_arg:
            self.add_argument(
                "--non-interactive",
                action="store_true",
                help="Run in non-interactive mode (disable prompts)",
            )
        if add_task_args:
            self._add_task_args()
        if add_force_arg:
            self.add_argument(
                "-f",
                "--force",
                action="store_true",
                help="Force execution of task(s) even if they don't need to run",
            )

    def _add_task_args(self) -> None:
        """
        Add common task arguments to the parser.

        :raises ArgumentTypeError: If argument validation fails
        """

        # Add system-info argument
        def json_dict(value: str) -> SystemInfo:
            """
            Validate that the input is a JSON object (dictionary).

            :param value: Input string
            :type value: str
            :return: Parsed JSON object
            :rtype: dict
            :raises ArgumentTypeError: If the input is not a valid JSON object
            """
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as e:
                raise ArgumentTypeError(f"Invalid JSON for --system-info: {e}")
            if not isinstance(parsed, dict):
                raise ArgumentTypeError(
                    "--system-info must be a JSON object (dictionary)"
                )
            return parsed

        self.add_argument(
            "--system-info",
            type=json_dict if self.allow_complex_types else str,
            required=True,
            help="JSON object with system information",
        )

        # Add config-file argument
        def existing_path(value: str) -> Path:
            """
            Validate that the input path exists.

            :param value: Input path string
            :type value: str
            :return: Path object
            :rtype: Path
            :raises ArgumentTypeError: If the path does not exist
            """
            path = Path(value)
            if not path.exists():
                raise ArgumentTypeError(f"Config file not found: {path}")
            return path

        self.add_argument(
            "--config-file",
            type=existing_path if self.allow_complex_types else str,
            default=None,
            help="Path to an existing config file",
        )

    def add_required_group(self, mutex: bool = False) -> _ArgumentGroup:
        """
        Add a 'required arguments' group to the parser.

        :param mutex: Whether the group is mutually exclusive
        :type mutex: bool
        :return: The created argument group
        :rtype: _ArgumentGroup
        """
        required = self.add_argument_group(self.required_group_title)
        if mutex:
            return required.add_mutually_exclusive_group(required=True)
        else:
            return required

    def extend_arguments(self, args_dict: ArgsDefinitionCollection) -> None:
        """
        Extend the parser with arguments defined in a plugin.

        :param args_dict: Dictionary of argument definitions
        :type args_dict: ArgsDefinitionCollection
        :raises ArgumentTypeError: If argument definitions are invalid
        """
        try:
            check_args_dict(args_dict)
        except ArgumentTypeError as e:
            raise ArgumentTypeError(
                f"Invalid argument definitions: {e}"
            ) from e

        # Collect mutually exclusive groups
        mutex_groups = defaultdict(list)
        for name, spec in args_dict.items():
            mutex = spec.get("mutex")
            if mutex:
                mutex_groups[mutex].append(name)
        argparse_mutex_groups = {
            name: self.add_mutually_exclusive_group() for name in mutex_groups
        }

        # Add arguments
        for name, spec in args_dict.items():
            kwargs = {"help": spec["help"]}  # To be passed to add_argument()

            default = spec.get("default")
            nargs = spec.get("nargs")
            choices = spec.get("choices")

            # Boolean flags
            if isinstance(default, bool):
                kwargs["action"] = "store_false" if default else "store_true"

            else:
                # Choices
                if choices is not None:
                    validator, metavar = _create_wildcard_validator(choices)
                    kwargs["type"] = validator
                    kwargs["metavar"] = metavar

                # All non-boolean argument types
                if default is not None:
                    # optional argument
                    kwargs["default"] = default
                elif nargs not in ("?", "*"):
                    # required argument
                    kwargs["required"] = True

                if nargs is not None:
                    kwargs["nargs"] = nargs

            # Choose correct target (parser or mutex group)
            mutex = spec.get("mutex")
            target = argparse_mutex_groups[mutex] if mutex else self

            # Finally, add the argument
            target.add_argument(name, **kwargs)

    def extend_task_arguments(self, task_name: str) -> None:
        """
        Extend the parser with task-specific arguments defined in a plugin, if any.

        :param task_name: Full name of a task in the form 'plugin_name/task_name'
        :type task_name: str
        :raises ValueError: If the plugin YAML could not be loaded
        """
        plugin = task_name.split("/", 1)[0]
        plugin_manifest: ResolvedPluginManifest = (
            _load_resolved_plugin_manifest(plugin)
        )
        if not plugin_manifest:
            raise ValueError(f"Plugin '{plugin}' could not be loaded")

        try:
            task_args = plugin_manifest["tasks"][task_name]["args"]
            self.extend_arguments(task_args)
        except KeyError as e:
            self.error(
                f"Key 'tasks'/'{task_name}'/'args' not found "
                f"in plugin '{plugin}' YAML. Broken link: {e}"
            )

    def _reorder_actions(self):
        """
        Reorder actions to have required ones first.
        """
        # Reorder action groups to have 'required arguments' first
        required_group = None
        for g in self._action_groups:
            if g.title == self.required_group_title:
                required_group = g
                break
        if required_group:
            self._action_groups.remove(required_group)
            self._action_groups.insert(0, required_group)

    def print_help(self, file=None) -> None:
        # Reorder action groups to have 'required arguments' first
        self._reorder_actions()

        # Call the original print_help
        return super().print_help(file)

    def parse_args(
        self, args: Sequence[str] | None = None, namespace: None = None
    ) -> Namespace:
        # Reorder action groups to have 'required arguments' first
        self._reorder_actions()

        # Call the original parse_args
        args = super().parse_args(args, namespace)

        # Get non-interactive mode from env var if not specified
        if self.add_non_interactive_arg and not args.non_interactive:
            args.non_interactive = (
                os.getenv("GURK_NON_INTERACTIVE", "false").lower()
                in YES_ANSWERS
            )

        return args


#########################################################################################
################################### Command utilities ###################################
#########################################################################################


def check_local_plugin(plugin_path: PathLike, verbose: bool = False) -> bool:
    """
    Check if a local plugin is valid.
        NOTE: All imported plugins (recursively) must also be local and valid.

    :param plugin_path: Path to the local plugin directory
    :type plugin_path: PathLike
    :param verbose: Whether to print errors
    :type verbose: bool
    :return: True if the plugin is valid, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Directed graphs for checking cycles
    imports_graph = nx.DiGraph()
    task_dependency_graph = nx.DiGraph()
    task_supercedes_graph = nx.DiGraph()

    # Save available tasks
    available_tasks: DefaultTaskDictCollection = dict()

    def _check_local_plugin(_plugin_path: Path) -> bool:
        def error(message: str) -> bool:
            if verbose:
                logger.error(f"'{_plugin_path}': {message}")

        # Load pyproject.toml
        pyproject_file = _plugin_path / "pyproject.toml"
        if not pyproject_file.is_file():
            error(
                f"Plugin source '{_plugin_path}' is missing a 'pyproject.toml' file."
            )
            return False
        pyproject_data = load_toml(pyproject_file)
        if not pyproject_data:
            error(
                f"Plugin source '{_plugin_path}' has an invalid 'pyproject.toml' file"
            )
            return False

        # Validate pyproject.toml
        project_metadata = PluginMetadata.filtered(pyproject_data)
        if not project_metadata:
            error(
                f"Plugin source '{_plugin_path}' has an invalid 'pyproject.toml' file: invalid 'project' section structure. Expected:"
            )
            if verbose:
                print_typed_dict_types(PluginMetadata)
            return False

        ## Unique plugin name
        plugin_name = project_metadata["name"]
        _, existing_plugin = _get_plugin_registration(plugin_name)
        if (
            existing_plugin
            and Path(existing_plugin["local"]) != _plugin_path.resolve()
        ):
            error(
                f"Plugin name '{plugin_name}' is already used by another plugin at '{existing_plugin['local']}'."
            )
            return False

        # Load manifest file
        plugin: PluginManifest = load_yaml(
            _plugin_path / GURK_MANIFEST_FILENAME
        )
        if plugin is None:
            error(
                f"Plugin source '{_plugin_path}' has no '{GURK_MANIFEST_FILENAME}' file or it is invalid YAML."
            )
            return False

        # Validate structure
        plugin_without_helpers: PluginManifest = {
            k: v
            for k, v in plugin.items()
            if isinstance(k, str) and not k.startswith("_")
        }
        if not validate_typed_dict(plugin_without_helpers, PluginManifest):
            error(
                f"Plugin at '{_plugin_path}' has invalid structure. Expected:"
            )
            if verbose:
                print_typed_dict_types(PluginManifest)
            return False

        ## Check each task field
        plugin_tasks = plugin.get("tasks", {})
        for task_name, task in plugin_tasks.items():
            # Check task name
            plugin_prefix, remaining = (task_name.split("/", 1) + [None])[:2]
            if plugin_prefix != plugin_name or not remaining:
                error(
                    f"Task '{task_name}' has an invalid name. Its name should be '{plugin_name}/<task_name>'"
                )
                return False

            # Check task description
            if not task["description"]:
                error(f"Task '{task_name}' description is missing or empty.")
                return False

            # Check 'script' field
            ## Existence
            script = _plugin_path / task["script"]
            if not script.is_file():
                error(
                    f"Task '{task_name}' script file '{script}' does not exist."
                )
                return False
            ## Validity
            errors = check_script_blocks(script)
            if errors:
                error(
                    f"Task '{task_name}' script '{script}' has errors:\n"
                    + "\n".join(errors)
                )
                return False

            # Check 'function' field
            blocks = get_block_spans(script)
            if task["function"] is None:
                desired_block_type = ScriptBlockTypes.ENTRYPOINT
            else:
                desired_block_type = ScriptBlockTypes.FUNCTION
            if not any(
                b["name"] == task["function"]
                for b in blocks
                if b["type"] == desired_block_type
            ):
                error(
                    f"Task '{task_name}' {'function ' + task['function'] if task['function'] else 'entrypoint'} does not exist in script '{script}'."
                )
                return False

            # Check 'config_file' field
            if task.get("config_file") is not None:
                config_file = _plugin_path / task["config_file"]
                if not config_file.is_file():
                    error(
                        f"Task '{task_name}' config file '{config_file}' does not exist."
                    )
                    return False

            # Check 'args' field
            task_args = task.get("args")
            if task_args:
                # Validate structure
                try:
                    check_args_dict(task_args)
                except ArgumentTypeError as e:
                    error(
                        f"Task '{task_name}' has invalid 'args' definition: {e}"
                    )
                    return False

                # Validate arg names
                arg_start = f"--{plugin_name}-"
                arg_names = [arg_name for arg_name in task_args.keys()]
                invalid_args = [
                    arg_name
                    for arg_name in arg_names
                    if not arg_name.startswith(arg_start)
                ]
                if invalid_args:
                    error(
                        f"Task '{task_name}' has an invalid arg names {invalid_args}. "
                        f"Arg names must be '{arg_start}<remaining>'."
                    )
                    return False

        # Check that the 'imports' section is valid
        imports = plugin.get("imports", [])
        if not isinstance(imports, list) or not all(
            isinstance(imp, str) for imp in imports
        ):
            error(
                f"Plugin 'imports' section is not a list of strings, but of type '{type(imports)}'."
            )
            return False

        def _check_graph_cycles(graph: nx.DiGraph, field: str) -> bool:
            """
            Check for cycles in a directed graph.

            :param graph: The directed graph to check
            :type graph: nx.DiGraph
            :param field: The field being checked (for logging purposes)
            :type field: str
            :return: True if no cycles are found, False otherwise
            :rtype: bool
            """
            try:
                cycle = nx.find_cycle(graph)
                if cycle:
                    error(
                        f"Circular dependency detected in '{field}' field: {cycle}"
                    )
                    return False
            except nx.NetworkXNoCycle:
                # No cycle detected
                pass
            return True

        ## Check that imported plugins exist and are valid
        imports_graph.add_node(plugin_name)
        for imp in imports:
            # Check that imported plugins exist in the desired location
            if not plugin_exists_locally(imp):
                msg = f"Imported plugin '{imp}' does not exist locally."
                if plugin_exists_remotely(imp):
                    msg += f" You can pull it via 'gurk pull {imp}'."
                error(msg)
                return False

            # Check the imports graph for cycles
            imports_graph.add_edge(plugin_name, imp)
            if not _check_graph_cycles(imports_graph, "imports"):
                return False

            # Check imported plugin
            if not _check_local_plugin(
                Path(_get_plugin_registration(imp)[1]["local"])
            ):
                error(f"Imported plugin '{imp}' is invalid.")
                return False

        # Add defined tasks to available tasks
        task_names = list(plugin_tasks.keys())
        available_tasks.update(plugin_tasks)

        def expand_graph(graph: nx.DiGraph, field: str) -> bool:
            """
            Expand a directed graph with edges from a task field.
                NOTE: The direction is the same, as this is only used for cycle detection.

            :param graph: The directed graph to expand
            :type graph: nx.DiGraph
            :param field: The field from which to add edges
            :type field: str
            :return: True if successful, False if an unknown task is found
            :rtype: bool
            """
            graph.add_nodes_from(task_names)
            for task_name, task in plugin_tasks.items():
                for dep in task.get(field, []):
                    if dep not in available_tasks:
                        error(
                            f"Task '{task_name}' uses unknown task '{dep}' in '{field}' field."
                        )
                        return False
                    graph.add_edge(task_name, dep)

            return True

        # Check the task dependency graph
        dependency_field = "depends_on"
        if not expand_graph(task_dependency_graph, dependency_field):
            return False
        elif not _check_graph_cycles(task_dependency_graph, dependency_field):
            return False

        # Check the task supercedes graph
        supercedes_field = "supercedes"
        if not expand_graph(task_supercedes_graph, supercedes_field):
            return False
        elif not _check_graph_cycles(task_supercedes_graph, supercedes_field):
            return False

        # Check 'options' section
        options: PluginOptions = plugin["options"]
        if "default" not in options:
            error(
                "Plugin 'options' section is missing required 'default' option."
            )
            return False

        ## Validate each option
        for option_name, option in options.items():
            # Check that all tasks in the option are defined
            for task_name in option.keys():
                if task_name not in available_tasks:
                    error(
                        f"Task '{task_name}' in '{option_name}' option "
                        "is not defined in this or any imported plugins."
                    )
                    return False

            # Check 'config_file' fields
            for task_name, task_spec in option.items():
                config_file = task_spec.get("config_file")
                if config_file:
                    config_file = _plugin_path / task_spec["config_file"]
                    if not config_file.is_file():
                        error(
                            f"Task '{task_name}' in option '{option_name}' "
                            f"config file '{config_file}' does not exist."
                        )
                        return False

            # Check that all args in the option are defined
            for task_name, option_spec in option.items():
                # Create a temporary parser to validate args
                parser = GurkArgumentParser(
                    add_verbose_arg=False,
                    add_non_interactive_arg=False,
                    add_force_arg=True,
                )
                allowed_args = available_tasks[task_name].get("args", {})
                parser.extend_arguments(allowed_args)

                # Override parser.error to raise exception instead of exiting
                def raise_error(message):
                    raise ValueError(message)

                parser.error = raise_error

                # Validate args
                try:
                    parser.parse_args(option_spec.get("args", []))
                except ValueError as e:
                    error(e)
                    return False

            # Check that at least one task is being run.
            # If any tasks are defined in the plugin, that at least one of them must be enabled
            enabled_tasks = {k: v for k, v in option.items() if v["enabled"]}
            if not enabled_tasks:
                error(f"Option '{option_name}' has no enabled tasks.")
                return False
            if plugin_tasks and not set(plugin_tasks.keys()) & set(
                enabled_tasks.keys()
            ):
                error(
                    f"Option '{option_name}' does not enable any tasks defined in this plugin."
                )
                return False

            # Check that no two tasks that supercede each other are enabled together
            for u, v in task_supercedes_graph.edges():
                if u in enabled_tasks and v in enabled_tasks:
                    error(
                        f"Tasks '{u}' and '{v}' that supercede each other are "
                        f"both enabled in the same option '{option_name}'."
                    )
                    return False

        # All checks passed
        return True

    # Check plugin
    return _check_local_plugin(Path(plugin_path))


def create_plugin_venv(plugin_name: str, dependencies: list[str]) -> bool:
    """
    Create a virtual environment for a plugin and install its dependencies.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :param dependencies: List of dependencies to install
    :type dependencies: list[str]
    :return: True if the virtual environment was created successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check if venv already exists
    venv_dir = PACKAGE_VENVS_PATH / plugin_name
    if venv_dir.is_dir():
        logger.error(
            f"Virtual environment for plugin '{plugin_name}' already exists at {venv_dir}"
        )
        return False

    # Create venv
    logger.info(
        f"Creating virtual environment for plugin '{plugin_name}' in {venv_dir}"
    )
    venv.EnvBuilder(with_pip=True).create(venv_dir)

    # Install dependencies
    pip_bin = str(venv_dir / "bin" / "pip")
    all_dependencies = dependencies + [PACKAGE_SRC_PATH.parents[1].as_posix()]
    logger.debug(
        f"Installing dependencies for plugin '{plugin_name}' in {venv_dir}: {dependencies}"
    )
    try:
        subprocess.check_call(
            [pip_bin, "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL
        )
        subprocess.check_call(
            [pip_bin, "install", *all_dependencies], stdout=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to install dependencies for plugin '{plugin_name}': {e}"
        )
        return False

    return True


def pull_local_plugin(
    plugin_path: PathLike, pull_imports: bool = True
) -> bool:
    """
    Import a plugin from a local directory.

    :param plugin_path: Path to the local plugin directory
    :type plugin_path: PathLike
    :param pull_imports: Whether to also pull imported plugins recursively
    :type pull_imports: bool
    :return: True if the plugin was imported successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Get plugin manifest
    plugin_path = Path(plugin_path)
    manifest_data: PluginManifest = load_yaml(
        plugin_path / GURK_MANIFEST_FILENAME
    )
    if not manifest_data:
        logger.error(
            f"Plugin at '{plugin_path}' has no '{GURK_MANIFEST_FILENAME}' file or it is empty/invalid YAML",
        )
        return False

    # Get plugin metadata
    metadata = load_toml(plugin_path / "pyproject.toml")
    if not metadata:
        logger.error(
            f"Plugin at '{plugin_path}' has an invalid or missing 'pyproject.toml' file",
        )
        return False

    # Extract relevant metadata
    try:
        plugin_name: str = metadata["project"]["name"]
    except KeyError as e:
        logger.error(
            f"Plugin at '{plugin_path}' has an invalid 'pyproject.toml' file: missing key {e}",
        )
        return False
    dependencies: list[str] = (
        metadata["project"].get("optional-dependencies", {}).get("gurk", [])
    )

    # Check if plugin with same name already exists
    if all(_get_plugin_registration(plugin_name)):
        logger.error(
            f"Plugin with name '{plugin_name}' already exists. Please "
            f"remove it via 'gurk remove {plugin_name}' first."
        )
        return False

    # Check validity of local plugin
    if not check_local_plugin(plugin_path, verbose=True):
        logger.error(
            f"Plugin at '{plugin_path}' is not a valid gurk plugin.",
        )
        return False

    # Add plugin registry entry
    if all(
        _get_plugin_registration(
            plugin_name, home_registry=False, require_local=False
        )[0]
    ):
        # Remote package plugin
        dest_path = PACKAGE_SRC_PATH / "plugins" / plugin_name

        registry_file = PACKAGE_SRC_PATH / "plugins" / "registry.yaml"
        registry = load_yaml(registry_file)
        registry[plugin_name] = {}
        registry[plugin_name]["local"] = str(dest_path)
        registry[plugin_name]["remote"] = None
        dump_yaml(registry, registry_file)
    else:
        # Regular plugin
        dest_path = PACKAGE_HOME_PATH / "plugins" / plugin_name

        add_plugin_entry(
            plugin_name,
            PluginRegistryEntry(
                local=str(dest_path),
                remote=None,
            ),
        )

    # Add plugin folder
    shutil.copytree(plugin_path, dest_path)

    # Install plugin dependencies in the plugin venv
    if not create_plugin_venv(plugin_name, dependencies):
        logger.error(
            f"Failed to create virtual environment for plugin '{plugin_name}'",
        )
        return False

    # Pull imported plugins recursively
    if pull_imports:
        for imp in manifest_data.get("imports", []):
            if not is_git_repo(imp):
                # Ignore local imports
                continue

            logger.info(f"Pulling imported plugin '{imp}'...")
            if not pull_plugin(imp, pull_imports):
                logger.error(
                    f"Failed to pull imported plugin '{imp}' for plugin '{plugin_path}'",
                )
                return False

    # Verify by getting plugin data
    try:
        get_plugin_data(plugin_name)
    except ModuleNotFoundError as e:
        logger.error(str(e))
        return False

    return True


def pull_plugin(plugin: GitRef, pull_imports: bool = True) -> bool:
    """
    Import a plugin from a remote Git repository.

    :param plugin: GitRef of the plugin to import
    :type plugin: GitRef
    :param pull_imports: Whether to also pull imported plugins recursively
    :type pull_imports: bool
    :return: True if the plugin was imported successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()
    logger.info(f"Pulling plugin from remote source '{plugin}'...")

    def error(message: str, _temp_path: Path | None = None):
        """
        Log an error message and clean up temporary plugin path if provided.

        :param message: Error message to log
        :type message: str
        :param _temp_path: Temporary plugin path to clean up
        :type _temp_path: Path | None
        """
        logger.error(message + ". Skipping...")
        if _temp_path is not None and _temp_path.exists():
            if _temp_path.is_dir():
                shutil.rmtree(_temp_path)
            else:
                _temp_path.unlink()

    # Import metadata to random file
    temp_metadata = generate_random_path(suffix=".toml", create=False)
    try:
        git_clone(edit_url(plugin, path="pyproject.toml"), temp_metadata)
    except subprocess.CalledProcessError as e:
        error(
            f"Failed to clone 'pyproject.toml' from "
            f"remote plugin repository '{plugin}': {e}",
            temp_metadata,
        )
        return False
    except ValueError as e:
        error(str(e), temp_metadata)
        return False

    # Get relevant metadata
    try:
        metadata = load_toml(temp_metadata)
        plugin_name: str = metadata["project"]["name"]
        plugin_version: str = metadata["project"]["version"]
        if not check_version(plugin_version):
            raise ValueError(f"Invalid version string: {plugin_version}")
    except KeyError as e:
        logger.error(
            f"Plugin '{plugin}' has an invalid 'pyproject.toml' file: invalid key {e}",
        )
        return False

    # Check if plugin already exists
    if installed_plugin_path(plugin_name):
        error(
            f"Plugin with remote '{plugin}' already exists locally. Please remove it "
            f"via 'gurk remove {plugin_name}' first or update it via 'gurk update {plugin_name}'"
        )
        return False

    # See if plugin source is valid
    if not plugin_exists_remotely(plugin):
        error(
            f"Remote plugin source '{plugin}' does not exist or is not a valid git repository"
        )
        return False

    # Import manifest to random file
    temp_manifest = generate_random_path(suffix=".yaml", create=False)
    try:
        git_clone(edit_url(plugin, path=GURK_MANIFEST_FILENAME), temp_manifest)
    except subprocess.CalledProcessError as e:
        error(
            f"Failed to clone '{GURK_MANIFEST_FILENAME}' "
            f"from remote plugin repository '{plugin}': {e}",
            temp_manifest,
        )
        return False

    # Determine relevant files
    relevant_files = {GURK_MANIFEST_FILENAME, "pyproject.toml"}
    try:
        # Load manifest file with basic validation
        manifest_data = load_yaml(temp_manifest)
        if not manifest_data:
            raise ValueError("Empty or invalid YAML")

        # Defined tasks
        tasks = manifest_data.get("tasks", {})
        if isinstance(tasks, dict):
            for task in tasks.values():
                if isinstance(task, dict):
                    # Script
                    script = task.get("script")
                    if not isinstance(script, str):
                        raise ValueError(
                            f"Invalid 'script' field in task: {task}"
                        )
                    relevant_files.add(script)

                    # Config file
                    config_file = task.get("config_file")
                    if config_file is not None and not isinstance(
                        config_file, str
                    ):
                        raise ValueError(
                            f"Invalid 'config_file' field in task: {task}"
                        )
                    elif config_file is not None:
                        relevant_files.add(config_file)
                else:
                    raise ValueError(
                        f"Invalid task type in 'tasks': {type(task)} (expected dict)"
                    )
        else:
            raise ValueError(
                f"Invalid 'tasks' section type: {type(tasks)} (expected dict)"
            )

        # Options
        options = manifest_data.get("options", {})
        if isinstance(options, dict):
            for option in options.values():
                if isinstance(option, dict):
                    for task in option.values():
                        # Config file
                        config_file = task.get("config_file")
                        if config_file is not None and not isinstance(
                            config_file, str
                        ):
                            raise ValueError(
                                f"Invalid 'config_file' field in task: {task}"
                            )
                        elif config_file is not None:
                            relevant_files.add(config_file)
                else:
                    raise ValueError(
                        f"Invalid task option type in 'options': {type(option)} (expected dict)"
                    )
        else:
            raise ValueError(
                f"Invalid 'options' section type: {type(options)} (expected dict)"
            )
    except Exception as e:
        error(
            f"Remote plugin repository '{plugin}' has an invalid '{GURK_MANIFEST_FILENAME}' file: {e}",
            temp_manifest,
        )
        return False

    # Clone only relevant files to temporary directory
    temp_plugin_path = generate_random_path(
        prefix="gurk_plugin_import_", create=False
    )
    for file in relevant_files:
        pullfile = edit_url(plugin, path=file)
        try:
            git_clone(pullfile, dest=temp_plugin_path / file)
        except subprocess.CalledProcessError:
            error(
                f"Failed to clone file '{file}' from remote plugin repository '{plugin}'",
                temp_plugin_path,
            )
            return False

    # Pull local plugin from temporary directory
    if not pull_local_plugin(temp_plugin_path, pull_imports):
        error(
            f"Failed to import plugin from remote repository '{plugin}'",
            temp_plugin_path,
        )
        return False

    # Upate plugin registry entry to include remote
    update_plugin_entry(
        plugin_name,
        remote=edit_url(extract_url(plugin), version=plugin_version),
    )

    # Clean up temporary plugin path
    shutil.rmtree(temp_plugin_path)

    logger.info(f"Successfully pulled plugin '{plugin_name}' from '{plugin}'")
    return True


def remove_plugin(plugin: PluginSpec, purge: bool = False) -> None:
    """
    Remove a locally installed plugin.

    :param plugin: Name, PathLike, or GitRef of the plugin to remove
    :type plugin: PluginSpec
    :param purge: Whether to also remove the plugin registry entry fully. Does not affect package registry entries.
    :type purge: bool
    :raises ModuleNotFoundError: If no such local plugin is found
    """
    # Get logger
    logger = get_logger()
    remove_msg = []

    # Get plugin data
    plugin_name, plugin_entry = _get_plugin_registration(
        plugin, require_local=False
    )
    if not (plugin_name and plugin_entry):
        raise ModuleNotFoundError(f"No such local plugin found: {plugin}")
    local = plugin_entry["local"]

    # Remove plugin registry entry
    _remove_plugin_entry(plugin, purge)
    remove_msg.append("registry entry")

    # Remove plugin folder
    if local:
        plugin_path = Path(local)
        if plugin_path.is_dir():
            shutil.rmtree(plugin_path)
        remove_msg.append("plugin files")

    # Remove plugin venv
    venv_path = PACKAGE_VENVS_PATH / plugin_name
    if venv_path.is_dir():
        shutil.rmtree(venv_path)
        remove_msg.append("virtual environment")

    logger.info(
        f"Successfully removed {' and '.join(remove_msg)} for plugin '{plugin_name}'"
    )
