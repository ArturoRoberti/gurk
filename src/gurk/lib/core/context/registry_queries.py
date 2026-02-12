from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeVar, overload

from gurk.lib.utils.configs import overlay_dicts
from gurk.lib.utils.git_query import extract_url
from gurk.lib.utils.typed_dict import (
    print_typed_dict_types,
    validate_typed_dict,
)

from .logger import get_logger
from .registry_manager import (
    RegistryManager,
    ZippedRegistry,
    _current_registries,
    _expand_registry_path,
    _get_registry_files,
    _zip_registry_files,
)
from .registry_types import (
    LocalPluginRegistryEntry,
    PluginRegistry,
    PluginRegistryEntry,
    RemotePluginRegistryEntry,
)

if TYPE_CHECKING:
    from gurk.lib.core.plugins.common import PluginSpecification


T = TypeVar("T")


@overload
def _filter_by_registries(
    tup: tuple[T, T],
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[False] = ...,
    dcopy: bool = ...,
) -> T:
    ...


@overload
def _filter_by_registries(
    tup: tuple[T, T],
    *,
    home_registry: Literal[False] = ...,
    package_registry: Literal[True] = ...,
    dcopy: bool = ...,
) -> T:
    ...


@overload
def _filter_by_registries(
    tup: tuple[T, T],
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[True] = ...,
    dcopy: bool = ...,
) -> tuple[T, T]:
    ...


def _filter_by_registries(
    tup: tuple[T, T],
    *,
    home_registry: bool,
    package_registry: bool,
    dcopy: bool = False,
) -> tuple[T, T] | T:
    """
    Filter a tuple by the requested registries.

    :param tup: Tuple to filter
    :type tup: tuple[T, T]
    :param home_registry: Whether to include the home registry
    :type home_registry: bool
    :param package_registry: Whether to include the package registry
    :type package_registry: bool
    :param dcopy: Whether to deepcopy the entries
    :type dcopy: bool
    :return: Filtered tuple or single entry, depending on the input
    :rtype: tuple[T, T] | T
    """
    filtered = []
    if home_registry:
        filtered.append(deepcopy(tup[0]) if dcopy else tup[0])
    if package_registry:
        filtered.append(deepcopy(tup[1]) if dcopy else tup[1])
    return filtered[0] if len(filtered) == 1 else tuple(filtered)


@overload
def get_registry_files(
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[False] = ...,
) -> Path:
    ...


@overload
def get_registry_files(
    *,
    home_registry: Literal[False] = ...,
    package_registry: Literal[True] = ...,
) -> Path:
    ...


@overload
def get_registry_files(
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[True] = ...,
) -> tuple[Path, Path]:
    ...


def get_registry_files(
    *, home_registry: bool, package_registry: bool
) -> tuple[Path, Path] | Path:
    """
    Get the registry files corresponding to the requested registries.

    :param home_registry: Whether to include the home plugin registry file
    :type home_registry: bool
    :param package_registry: Whether to include the package plugin registry file
    :type package_registry: bool
    :return: Tuple of plugin registry files (home, package), depending on the input
    :rtype: tuple[Path, Path] | Path
    """
    return _filter_by_registries(
        _get_registry_files(),
        home_registry=home_registry,
        package_registry=package_registry,
    )


def _get_registries() -> tuple[PluginRegistry, PluginRegistry]:
    """
    Get the currently active registrator's plugin registries without deepcopying
    them (for internal use only). Also deletes invalid entries before returning.

    :return: Tuple of plugin registries (home, package)
    :rtype: tuple[PluginRegistry, PluginRegistry]
    :raises RuntimeError: If no registrator is initialized
    """
    registries = _current_registries.get()
    if registries is None:
        raise RuntimeError("RegistryManager not initialized")

    return registries


@overload
def get_registries(
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[False] = ...,
    combine: Literal[False] = ...,
) -> PluginRegistry:
    ...


@overload
def get_registries(
    *,
    home_registry: Literal[False] = ...,
    package_registry: Literal[True] = ...,
    combine: Literal[False] = ...,
) -> PluginRegistry:
    ...


@overload
def get_registries(
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[True] = ...,
    combine: Literal[False] = ...,
) -> tuple[PluginRegistry, PluginRegistry]:
    ...


@overload
def get_registries(
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[True] = ...,
    combine: Literal[True] = ...,
) -> PluginRegistry:
    ...


def get_registries(
    *, home_registry: bool, package_registry: bool, combine: bool = False
) -> tuple[PluginRegistry, ...] | PluginRegistry:
    """
    Get the currently active registrator's plugin registries.

    :param home_registry: Whether to include the home plugin registry
    :type home_registry: bool
    :param package_registry: Whether to include the package plugin registry
    :type package_registry: bool
    :param combine: Whether to combine the home and package plugin registries into one, with the home registry prioritized
    :type combine: bool
    :return: Tuple of plugin registries (home, package), or a single (combined) registry, depending on the input
    :rtype: tuple[PluginRegistry, ...] | PluginRegistry
    :raises ValueError: If neither home_registry nor package_registry is True, or if combine is True while not both home_registry and package_registry are True
    :raises RuntimeError: If no registrator is initialized
    """
    # Validate input
    if not home_registry and not package_registry:
        raise ValueError(
            "At least one of home_registry or package_registry must be True"
        )
    if combine and not (home_registry and package_registry):
        raise ValueError(
            "Combine can only be True if both home_registry and package_registry are True"
        )

    # Filter registries based on input
    filtered = _filter_by_registries(
        _get_registries(),
        home_registry=home_registry,
        package_registry=package_registry,
        dcopy=True,
    )

    if combine:
        return overlay_dicts(filtered)
    else:
        return filtered


@overload
def get_zipped_registries(
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[False] = ...,
) -> ZippedRegistry:
    ...


@overload
def get_zipped_registries(
    *,
    home_registry: Literal[False] = ...,
    package_registry: Literal[True] = ...,
) -> ZippedRegistry:
    ...


@overload
def get_zipped_registries(
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[True] = ...,
) -> tuple[ZippedRegistry, ZippedRegistry]:
    ...


def get_zipped_registries(
    *, home_registry: bool, package_registry: bool
) -> tuple[ZippedRegistry, ZippedRegistry] | ZippedRegistry:
    """
    Get a tuple of tuples of plugin registry files and their corresponding registries, with the home one first.

    :param home_registry: Whether to include the home plugin registry
    :type home_registry: bool
    :param package_registry: Whether to include the package plugin registry
    :type package_registry: bool
    :return: Tuple of tuples of plugin registry files and their corresponding registries (home, package), depending on the input
    :rtype: tuple[ZippedRegistry, ZippedRegistry] | ZippedRegistry
    """
    _registries = get_registries(home_registry=True, package_registry=True)
    return _filter_by_registries(
        _zip_registry_files(_registries),
        home_registry=home_registry,
        package_registry=package_registry,
    )


def _get_plugin_registration(
    plugin: "PluginSpecification",
    *,
    package_registry: bool,
    require_local: bool,
) -> PluginRegistry | None:
    # Get the plugin registry file and registry
    registry_file, registry = get_zipped_registries(
        home_registry=not package_registry, package_registry=package_registry
    )

    # Access plugin entry
    name_via_remote = next(
        (
            k
            for k, v in registry.items()
            if v.get("remote")
            and extract_url(str(plugin)) == extract_url(v["remote"])
        ),
        None,
    )
    name_via_local = next(
        (
            k
            for k, v in registry.items()
            if v.get("local") is not None
            and _expand_registry_path(registry_file, v["local"])
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
        return None
    entry = registry[name]

    # Validate that it has a valid local path (if required)
    if require_local and (
        entry["local"] is None
        or not _expand_registry_path(registry_file, entry["local"]).is_dir()
    ):
        return None

    return {name: entry}


def get_available_plugin_names() -> set[str]:
    """
    Get the names of all available local plugins, extracted from the combined registry keys.

    :return: List of available local plugin names
    :rtype: list[str]
    """
    combined_registry = get_registries(
        home_registry=True, package_registry=True, combine=True
    )
    return set(combined_registry.keys())


def get_plugin_registration(
    plugin: "PluginSpecification",
    *,
    home_registry: bool,
    package_registry: bool,
    require_local: bool = True,
) -> PluginRegistry | None:
    """
    Get the registry entry of a plugin (path, remote) if it exists locally.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: "PluginSpecification"
    :param home_registry: Whether to check the home plugin registry (takes precedence over the package registry if both are True)
    :type home_registry: bool
    :param package_registry: Whether to check the package plugin registry
    :type package_registry: bool
    :param require_local: Whether to only return entries with a local path
    :type require_local: bool
    :return: Registry entry if the plugin exists locally, None otherwise
    :rtype: PluginRegistry | None
    :raises RuntimeError: If no registrator is initialized
    """
    # Collect registrations
    registrations = tuple(
        _get_plugin_registration(
            plugin,
            package_registry=pr,
            require_local=require_local,
        )
        for ind, pr in enumerate((False, True))
        if (home_registry, package_registry)[ind]
    )
    registrations = tuple(
        r for r in registrations if r
    )  # Filter out None results

    # Logging
    logger = get_logger()
    if not registrations:
        return None
    elif len(registrations) > 1:
        logger.debug(
            f"WARNING: Multiple registry entries found for plugin '{plugin}'. Using the home one."
        )

    return registrations[0]


def is_plugin_registered(
    plugin: "PluginSpecification",
    *,
    home_registry: bool,
    package_registry: bool,
    require_local: bool = True,
) -> bool:
    """
    Check if a plugin is registered locally in the currently active registrator's plugin registry.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: "PluginSpecification"
    :param home_registry: Whether to check the home plugin registry (takes precedence over the package registry if both are True)
    :type home_registry: bool
    :param package_registry: Whether to check the package plugin registry
    :type package_registry: bool
    :param require_local: Whether to only consider entries with a local path as registered
    :type require_local: bool
    :return: Whether the plugin is registered locally
    :rtype: bool
    :raises RuntimeError: If no registrator is initialized
    """
    registration = get_plugin_registration(
        plugin,
        home_registry=home_registry,
        package_registry=package_registry,
        require_local=require_local,
    )
    return registration is not None


def update_registry(
    plugin_name: str,
    entry: LocalPluginRegistryEntry | RemotePluginRegistryEntry | None,
    *,
    package_registry: bool | None = None,
    infer_local: bool = False,
    exist_ok: bool = True,
) -> bool:
    """
    Update the currently active registrator's plugin registry with a new entry.

    :param plugin_name: Name of the plugin to update
    :type plugin_name: str
    :param entry: Plugin registry entry to add or update, or None to remove the entry
    :type entry: LocalPluginRegistryEntry | RemotePluginRegistryEntry | None
    :param package_registry: Whether to update the package plugin registry (if False, updates the home registry). If None, tries to determine on where the plugin is already registered and returns False if it cannot be determined (i.e. when adding a new plugin)
    :type package_registry: bool | None
    :param infer_local: Whether to infer the "local" value of the entry (does not apply when already specified or when removing an entry)
    :type infer_local: bool
    :param exist_ok: Whether to allow updating an existing entry (if False, raises an error if the entry already exists)
    :type exist_ok: bool
    :return: True if the registry was updated, False otherwise
    :rtype: bool
    :raises RuntimeError: If no registrator is initialized
    """
    # Get logger
    logger = get_logger()

    def debug_error(message: str) -> None:
        logger.debug(
            f"ERROR: Invalid 'entry' value passed for updating plugin '{plugin_name}': {message}"
        )

    # Validate input
    if entry is not None:
        if not (
            validate_typed_dict(entry, LocalPluginRegistryEntry)
            or validate_typed_dict(entry, RemotePluginRegistryEntry)
        ):
            debug_error(
                f"'entry' has an invalid structure. Expected (e):\n"
                f"{print_typed_dict_types(PluginRegistryEntry, indent=2, as_str=True)}"
                f"but got:\n{logger.pprint_dict(entry, indent=2, as_str=True)}"
            )
            return False
        if not (infer_local or entry.get("local")) and not entry.get("remote"):
            debug_error("'entry' must have at least a local or remote value.")
            return False

    # Get registries
    registries = _get_registries()

    # Determine registry
    if package_registry is None:
        if is_plugin_registered(
            plugin_name,
            home_registry=True,
            package_registry=False,
            require_local=False,
        ):
            package_registry = False
        elif is_plugin_registered(
            plugin_name,
            home_registry=False,
            package_registry=True,
            require_local=False,
        ):
            package_registry = True
        else:
            logger.debug(
                "Could not determine registry, since it is registered in "
                "neither registry. Defaulting to home registry for new entry."
            )
            package_registry = False
    registry_index = int(package_registry)
    registry_str = "package" if package_registry else "home"
    registry_file = _get_registry_files()[registry_index]

    # Update registry
    if (
        entry is not None
        and plugin_name in registries[registry_index]
        and not exist_ok
    ):
        debug_error(f"Entry already exists in the {registry_str} registry")
        return False
    else:
        if entry is None:
            # Remove registration
            if package_registry and plugin_name in registries[registry_index]:
                # Can't fully remove package plugins' registration
                if registries[registry_index][plugin_name].get("remote"):
                    registries[registry_index][plugin_name]["local"] = None
                    return True
                else:
                    debug_error(
                        f"Cannot remove plugin '{plugin_name}' from the {registry_str} registry "
                        "since it does not have a remote. If you still want to remove it, please "
                        f"remove the plugin directory ({registry_file.parent / plugin_name}) "
                        f"and its entry from the registry file ({registry_file}) manually."
                    )
                    return False
            else:
                registries[registry_index].pop(plugin_name, None)
                return True
        else:
            # Infer local path if applicable
            if infer_local and not entry.get("local"):
                entry["local"] = str(registry_file.parent / plugin_name)

            # Add/update registration
            overlayed = overlay_dicts(
                [registries[registry_index].get(plugin_name, {}), entry]
            )
            if RegistryManager.is_entry_valid(
                plugin_name, overlayed, registry_file, check_local=False
            ):
                registries[registry_index][plugin_name] = overlayed
                return True
            else:
                debug_error(
                    f"Cannot add/update registration in {registry_str} "
                    "registry, as the resulting entry would be invalid/incomplete."
                )
                return False
