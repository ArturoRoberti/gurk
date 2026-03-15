# Copyright 2026 Arturo Roberti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from typing import Literal, NotRequired, TypedDict, overload

from gurk.lib.shared.dicts import pprint_dict, pprint_typed_dict
from gurk.lib.shared.plugins import (
    PluginRegistryEntry,
    PluginSpecification,
    ResolvedPluginRegistry,
    ResolvedZippedRegistry,
)
from gurk.lib.shared.remotes import GitQuery, extract_url
from gurk.lib.utils import PathLike, full_isinstance, overlay_dicts, typecheck

from ..logger import get_logger
from .registry_manager import _get_registries
from .registry_utils import (
    _expand_registry_path,
    _filter_by_registries,
    _get_registry_files,
    _is_entry_valid,
    _zip_registry_files,
)


@overload
def get_registry_files(
    *,
    public: Literal[True] = ...,
    private: Literal[False] = ...,
) -> Path: ...


@overload
def get_registry_files(
    *,
    public: Literal[False] = ...,
    private: Literal[True] = ...,
) -> Path: ...


@overload
def get_registry_files(
    *,
    public: Literal[True] = ...,
    private: Literal[True] = ...,
) -> tuple[Path, Path]: ...


@typecheck
def get_registry_files(
    *, public: bool, private: bool
) -> tuple[Path, Path] | Path:
    """
    Get the registry files corresponding to the requested registries.

    :param public: Whether to include the public plugin registry file
    :type public: bool
    :param private: Whether to include the private plugin registry file
    :type private: bool
    :return: Tuple of plugin registry files (public, private), depending on the input
    :rtype: tuple[Path, Path] | Path
    """
    return _filter_by_registries(
        _get_registry_files(),
        public=public,
        private=private,
    )


@overload
def get_registries(
    *,
    public: Literal[True] = ...,
    private: Literal[False] = ...,
    combine: Literal[False] = ...,
) -> ResolvedPluginRegistry: ...


@overload
def get_registries(
    *,
    public: Literal[False] = ...,
    private: Literal[True] = ...,
    combine: Literal[False] = ...,
) -> ResolvedPluginRegistry: ...


@overload
def get_registries(
    *,
    public: Literal[True] = ...,
    private: Literal[True] = ...,
    combine: Literal[False] = ...,
) -> tuple[ResolvedPluginRegistry, ResolvedPluginRegistry]: ...


@overload
def get_registries(
    *,
    public: Literal[True] = ...,
    private: Literal[True] = ...,
    combine: Literal[True] = ...,
) -> ResolvedPluginRegistry: ...


@typecheck
def get_registries(
    *, public: bool, private: bool, combine: bool = False
) -> tuple[ResolvedPluginRegistry, ...] | ResolvedPluginRegistry:
    """
    Get the currently active registrator's plugin registries.

    :param public: Whether to include the public plugin registry
    :type public: bool
    :param private: Whether to include the private plugin registry
    :type private: bool
    :param combine: Whether to combine the public and private plugin registries into one, with the public registry prioritized
    :type combine: bool
    :return: Tuple of plugin registries (public, private), or a single (combined) registry, depending on the input
    :rtype: tuple[ResolvedPluginRegistry, ...] | ResolvedPluginRegistry
    :raises ValueError: If neither public nor private is True, or if combine is True while not both public and private are True
    :raises RuntimeError: If no registrator is initialized
    """
    # Validate input
    if not public and not private:
        raise ValueError("At least one of public or private must be True")
    if combine and not (public and private):
        raise ValueError(
            "Combine can only be True if both public and private are True"
        )

    # Filter registries based on input
    filtered = _filter_by_registries(
        _get_registries(),
        public=public,
        private=private,
        dcopy=True,
    )

    if combine:
        return overlay_dicts(filtered)
    else:
        return filtered


@overload
def _get_zipped_registries(
    *,
    public: Literal[True] = ...,
    private: Literal[False] = ...,
) -> ResolvedZippedRegistry: ...


@overload
def _get_zipped_registries(
    *,
    public: Literal[False] = ...,
    private: Literal[True] = ...,
) -> ResolvedZippedRegistry: ...


@overload
def _get_zipped_registries(
    *,
    public: Literal[True] = ...,
    private: Literal[True] = ...,
) -> tuple[ResolvedZippedRegistry, ResolvedZippedRegistry]: ...


@typecheck
def _get_zipped_registries(
    *, public: bool, private: bool
) -> (
    tuple[ResolvedZippedRegistry, ResolvedZippedRegistry]
    | ResolvedZippedRegistry
):
    """
    Get a tuple of tuples of plugin registry files and their corresponding registries, with the public one first.

    :param public: Whether to include the public plugin registry
    :type public: bool
    :param private: Whether to include the private plugin registry
    :type private: bool
    :return: Tuple of tuples of plugin registry files and their corresponding registries (public, private), depending on the input
    :rtype: tuple[ResolvedZippedRegistry, ResolvedZippedRegistry] | ResolvedZippedRegistry
    """
    _registries = get_registries(public=True, private=True)
    return _filter_by_registries(
        _zip_registry_files(_registries),
        public=public,
        private=private,
    )


@typecheck
def _get_plugin_registration(
    plugin: PluginSpecification,
    *,
    private: bool,
    require_local: bool,
) -> ResolvedPluginRegistry | None:
    """
    Get the registry entry of a plugin (path, remote) if it exists locally.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :param private: Whether to check the private plugin registry (True) or the public plugin registry (False)
    :type private: bool
    :param require_local: Whether to only return entries with a local path
    :type require_local: bool
    :return: Registry entry if the plugin exists locally, None otherwise
    :rtype: ResolvedPluginRegistry | None
    :raises RuntimeError: If no registrator is initialized
    """
    # Get the plugin registry file and registry
    registry_file, registry = _get_zipped_registries(
        public=not private, private=private
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
    if str(plugin) in registry:
        # Access plugin by name
        name = str(plugin)
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
    combined_registry = get_registries(public=True, private=True, combine=True)
    return set(combined_registry.keys())


@typecheck
def get_plugin_registration(
    plugin: PluginSpecification,
    *,
    public: bool,
    private: bool,
    require_local: bool = True,
) -> ResolvedPluginRegistry | None:
    """
    Get the registry entry of a plugin (path, remote) if it exists locally.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :param private: Whether to check the private plugin registry (True) or the public plugin registry (False)
    :type private: bool
    :param require_local: Whether to only return entries with a local path
    :type require_local: bool
    :return: Registry entry if the plugin exists locally, None otherwise
    :rtype: ResolvedPluginRegistry | None
    :raises RuntimeError: If no registrator is initialized
    """
    # Collect registrations
    registrations = tuple(
        _get_plugin_registration(
            plugin,
            private=pr,
            require_local=require_local,
        )
        for ind, pr in enumerate((False, True))
        if (public, private)[ind]
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
            f"WARNING: Multiple registry entries found for plugin '{plugin}'. Using the public one."
        )

    return registrations[0]


@typecheck
def is_plugin_registered(
    plugin: PluginSpecification,
    *,
    public: bool,
    private: bool,
    require_local: bool = True,
) -> bool:
    """
    Check if a plugin is registered locally in the currently active registrator's plugin registry.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :param public: Whether to check the public plugin registry (takes precedence over the private registry if both are True)
    :type public: bool
    :param private: Whether to check the private plugin registry
    :type private: bool
    :param require_local: Whether to only consider entries with a local path as registered
    :type require_local: bool
    :return: Whether the plugin is registered locally
    :rtype: bool
    :raises RuntimeError: If no registrator is initialized
    """
    registration = get_plugin_registration(
        plugin,
        public=public,
        private=private,
        require_local=require_local,
    )
    return registration is not None


class LocalPluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | PathLike
    remote:  NotRequired[None | GitQuery]
    # fmt: on


class RemotePluginRegistryEntry(TypedDict):
    # fmt: off
    local:   NotRequired[None | PathLike]
    remote:  None | GitQuery
    # fmt: on


@typecheck
def update_registry(
    plugin_name: str,
    entry: LocalPluginRegistryEntry | RemotePluginRegistryEntry | None,
    *,
    private: bool | None = None,
    infer_local: bool = False,
    exist_ok: bool = True,
) -> bool:
    """
    Update the currently active registrator's plugin registry with a new entry.

    :param plugin_name: Name of the plugin to update
    :type plugin_name: str
    :param entry: Plugin registry entry to add or update, or None to remove the entry
    :type entry: LocalPluginRegistryEntry | RemotePluginRegistryEntry | None
    :param private: Whether to update the private plugin registry (if False, updates the public registry). If None, tries to determine on where the plugin is already registered and returns False if it cannot be determined (i.e. when adding a new plugin)
    :type private: bool | None
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
            full_isinstance(entry, LocalPluginRegistryEntry)
            or full_isinstance(entry, RemotePluginRegistryEntry)
        ):
            debug_error(
                f"'entry' has an invalid structure. Expected:\n"
                f"{pprint_typed_dict(PluginRegistryEntry, indent=2, as_str=True)}"
                f"but got:\n{pprint_dict(entry, indent=2, as_str=True)}"
            )
            return False
        if not (
            infer_local or entry.get("local") is not None
        ) and not entry.get("remote"):
            debug_error("'entry' must have at least a local or remote value.")
            return False

    # Get registries
    registries = _get_registries()

    # Determine registry
    if private is None:
        if is_plugin_registered(
            plugin_name,
            public=True,
            private=False,
            require_local=False,
        ):
            private = False
        elif is_plugin_registered(
            plugin_name,
            public=False,
            private=True,
            require_local=False,
        ):
            private = True
        else:
            logger.debug(
                "Could not determine registry, since it is registered in "
                "neither registry. Defaulting to public registry for new entry."
            )
            private = False
    registry_index = int(private)
    registry_str = "private" if private else "public"
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
            if private and plugin_name in registries[registry_index]:
                # Can't fully remove private plugins' registration
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
            if infer_local and entry.get("local") is None:
                entry["local"] = registry_file.parent / plugin_name
            elif entry.get("local") is not None:
                entry["local"] = Path(entry["local"]).expanduser()

            # Add/update registration
            overlayed = overlay_dicts(
                [registries[registry_index].get(plugin_name, {}), entry]
            )
            if _is_entry_valid(
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
