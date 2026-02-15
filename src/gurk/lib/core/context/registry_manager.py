from __future__ import annotations

import shutil
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Literal,
    NotRequired,
    TypeAlias,
    TypedDict,
    TypeVar,
    get_type_hints,
    overload,
)

from gurk.lib.utils.common import (
    PACKAGE_HOME_PATH,
    PACKAGE_SRC_PATH,
    PACKAGE_VENVS_PATH,
    PathLike,
    typecheck,
)
from gurk.lib.utils.configs import dump_yaml, load_yaml, overlay_dicts
from gurk.lib.utils.remotes import (
    GitQuery,
    GitQueryDict,
    extract_url,
    is_git_repo,
    parse_git_query,
)
from gurk.lib.utils.typed_dict import full_isinstance, print_typed_dict_types

from .logger import get_logger

if TYPE_CHECKING:
    from gurk.lib.core.plugins.common import PluginSpecification
else:
    # Runtime alias to keep pydantic's type evaluation happy without creating an import cycle
    PluginSpecification = str | PathLike | GitQuery


@typecheck
def _deepcopy_tuple(tup: tuple) -> tuple:
    """
    Deepcopy a tuple by deepcopying each item and returning a new tuple.

    :param tup: Tuple to deepcopy
    :type tup: tuple
    :return: Deepcopied tuple
    :rtype: tuple
    """
    return tuple(deepcopy(item) for item in tup)


class PluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | Path
    remote:  None | GitQuery
    # fmt: on


PluginRegistry: TypeAlias = dict[str, PluginRegistryEntry]


@typecheck
def get_plugin_directories(
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
    :raises TypeError: If an expected plugin directory path exists but is not a directory
    """
    parent_paths: list[Path] = []
    if home_registry:
        parent_paths.append(PACKAGE_HOME_PATH)
    if package_registry:
        parent_paths.append(PACKAGE_SRC_PATH)

    possible_plugin_paths = [p / "plugins" for p in parent_paths]
    for p in possible_plugin_paths:
        if p.is_file():
            raise TypeError(
                f"Expected plugin directory at '{p.as_posix()}', but "
                "found a file. Please remove or rename this file."
            )
        p.mkdir(parents=True, exist_ok=True)

    return tuple(possible_plugin_paths)


def _get_registry_files() -> tuple[Path, Path]:
    """
    Get a tuple of plugin registries, with the home one first.

    :return: Tuple of plugin registries (home, package)
    :rtype: tuple[Path, Path]
    """
    plugin_registry_files = [
        p / "registry.yaml" for p in get_plugin_directories()
    ]
    for p in plugin_registry_files:
        p.touch(exist_ok=True)

    return tuple(plugin_registry_files)


ZippedRegistry: TypeAlias = tuple[Path, PluginRegistry]


def _zip_registry_files(
    registries: tuple[PluginRegistry, PluginRegistry]
) -> tuple[ZippedRegistry, ...]:
    """
    Zip the plugin registries with their corresponding registry files, with the home one first.

    :param registries: Tuple of plugin registries (home, package)
    :type registries: tuple[PluginRegistry, PluginRegistry]
    :return: Tuple of tuples of plugin registry files and their corresponding registries (home, package)
    :rtype: tuple[ZippedRegistry, ...]
    """
    return tuple(zip(_get_registry_files(), registries))


@typecheck
def _expand_registry_path(
    registry_file: PathLike, path: PathLike, collapse: bool = False
) -> Path:
    """
    Expand the "local" path of a plugin registry entry to an absolute path based on the registry file's location.

    :param registry_file: Path to the registry file
    :type registry_file: PathLike
    :param path: Path to expand
    :type path: PathLike
    :param collapse: Whether to collapse the path instead of expanding it
    :type collapse: bool
    :return: Expanded plugin registry entry
    :rtype: Path
    """
    registry_file = Path(registry_file).expanduser()
    if collapse:
        return Path(path).relative_to(registry_file.parent)
    else:
        return (registry_file.parent / path).expanduser().resolve()


@typecheck
def _is_entry_valid(
    name: str,
    entry: PluginRegistryEntry,
    registry_file: Path,
    check_local: bool = True,
) -> bool:
    """
    Check if a plugin registry entry is valid.

    :param name: Name of the plugin
    :param entry: Plugin registry entry to validate
    :param registry_file: Path to the registry file
    :param check_local: Whether to check that the local path exists on disk (if specified).
    :return: Whether the entry is valid
    """
    checks: dict[str, bool] = {
        "Plugin name must be a string": isinstance(name, str),
        "Entry must conform to PluginRegistryEntry schema": full_isinstance(
            entry, PluginRegistryEntry
        ),
        "Entry must define at least one of 'local' or 'remote'": any(
            (entry.get("local") is not None, entry.get("remote") is not None)
        ),
        "Local path must exist if specified": (
            entry.get("local") is None
            or (
                not check_local
                or _expand_registry_path(
                    registry_file, entry["local"]
                ).is_dir()
            )
        ),
        "Remote must be a valid git repository if specified": (
            entry.get("remote") is None or is_git_repo(entry["remote"])
        ),
        "Remote must define a commit (and nothing else) if specified": (
            entry.get("remote") is None
            or (
                parse_git_query(entry["remote"])["commit"] is not None
                and all(
                    parse_git_query(entry["remote"])[f] is None
                    for f in get_type_hints(GitQueryDict)
                    if f not in ("url", "commit")
                )
            )
        ),
    }

    failed_checks = [msg for msg, passed in checks.items() if not passed]

    if failed_checks:
        failed_msgs = "\n- " + "\n- ".join(failed_checks)
        get_logger().debug(
            f"Invalid plugin registry entry '{name}' in "
            f"{registry_file.as_posix()}:{failed_msgs}"
        )
        return False

    return True


_current_registries = ContextVar("current_registries", default=None)


class RegistryManager:
    """Context manager to set a registry manager globally."""

    def __init__(self, *, writable: bool):
        self.writable = writable
        self._token = None
        self.registries = None

    def __enter__(self):
        # Check that a logger is active
        try:
            get_logger()
        except RuntimeError:
            raise RuntimeError(
                "Logger must be initialized before the registrator"
            )

        # Load registries and clean up invalidities
        self.load_registries()

        # make this globally visible
        registries = (
            self.registries
            if self.writable
            else _deepcopy_tuple(self.registries)
        )
        self._token = _current_registries.set(registries)

        return self

    def __exit__(self, exc_type, exc, tb):
        # restore previous registrator
        _current_registries.reset(self._token)

        # Write valid entries to registry file and clean up invalidities
        if self.writable and (
            exc_type is None
            or (exc_type is SystemExit and getattr(exc, "code", None) == 0)
        ):
            self.dump_registries()

        # Propagate exceptions
        return False

    def _delete_invalid_registrations(self) -> None:
        """
        Delete invalid plugin registry entries from the given registries.

        :param registries: Tuple of plugin registries (home, package)
        :type registries: tuple[PluginRegistry, PluginRegistry]
        """
        # Get logger
        logger = get_logger()

        # Delete registrations with invalid structure
        for is_package_registry, (registry_file, registry) in enumerate(
            _zip_registry_files(self.registries)
        ):
            for name, entry in deepcopy(registry).items():
                if not _is_entry_valid(name, entry, registry_file):
                    local_msg = "local path of " if is_package_registry else ""
                    warn_msg = (
                        f"Removing {local_msg}invalid plugin registry entry "
                        f"'{name}' from {registry_file.as_posix()}."
                    )
                    if not is_package_registry:
                        logger.warning(warn_msg)
                        del registry[name]
                    elif (
                        full_isinstance(entry, PluginRegistryEntry)
                        and entry.get("remote") is not None
                    ):
                        logger.warning(warn_msg)
                        registry[name]["local"] = None
                    else:
                        logger.error(
                            "THIS SHOULD NOT HAPPEN: Package registry entry "
                            f"'{name}' in {registry_file.as_posix()} is VERY "
                            "invalid, and is thus being removed entirely."
                        )
                        del registry[name]

        # Remove any home registry entries that also exist in the package registry
        home_registry, package_registry = self.registries
        for plugin_name in package_registry.keys():
            if plugin_name in home_registry:
                logger.warning(
                    f"Removing duplicate registry entry '{plugin_name}' from the home registry."
                )
                del home_registry[plugin_name]

    def _delete_unregistered_plugin_directories(self) -> None:
        """
        Remove any plugin directories that are not registered in the currently active registrator's plugin registry.
        """
        local_plugin_paths = {
            _expand_registry_path(rf, v["local"])
            for rf, r in _zip_registry_files(self.registries)
            for v in r.values()
            if v.get("local") is not None
        }
        for base_dir, registry_file in zip(
            get_plugin_directories(), _get_registry_files()
        ):
            for possible_plugin_dir in base_dir.iterdir():
                if (
                    possible_plugin_dir != registry_file
                    and possible_plugin_dir.name != "template"
                    and possible_plugin_dir not in local_plugin_paths
                ):
                    _type = (
                        "directory" if possible_plugin_dir.is_dir() else "file"
                    )
                    get_logger().warning(
                        f"Deleting invalid {_type} in plugins directory: {possible_plugin_dir.as_posix()}"
                    )
                    shutil.rmtree(possible_plugin_dir)

    def _delete_unregistered_venv_directories(self) -> None:
        """
        Remove any plugin venv directories that do not correspond to a registered plugin in the currently active registrator's plugin registry.
        """
        # Get all registered plugin names with local paths
        combined_registry = overlay_dicts(_deepcopy_tuple(self.registries))
        installed_plugin_names = set(
            k
            for k, v in combined_registry.items()
            if v.get("local") is not None
        )

        # Delete any venv directories that don't correspond to a registered plugin
        for dir in PACKAGE_VENVS_PATH.iterdir():
            if not dir.is_dir() or dir.name not in installed_plugin_names:
                _type = "directory" if dir.is_dir() else "file"
                get_logger().warning(
                    f"Deleting invalid {_type} in venvs directory: {dir.as_posix()}"
                )
                shutil.rmtree(dir)

    def cleanup(self) -> None:
        # Remove invalid registry entries
        self._delete_invalid_registrations()

        # Remove unregistered plugin directories
        self._delete_unregistered_plugin_directories()

        # Delete any venv directories that don't correspond to a plugin
        self._delete_unregistered_venv_directories()

    def load_registries(self) -> tuple[PluginRegistry, PluginRegistry]:
        """
        Load the plugin registries from their corresponding files, validating their structure and prepending the path to local entries.

        :return: Tuple of plugin registries (home, package)
        :rtype: tuple[PluginRegistry, PluginRegistry]
        """
        # Load registry files
        self.registries = tuple(
            load_yaml(p) or {} for p in _get_registry_files()
        )
        for ind, registry in enumerate(_deepcopy_tuple(self.registries)):
            if not isinstance(registry, dict):
                self.registries[ind] = {}

        # Make 'local' entries Path objects and prepend registry path
        for registry_file, registry in _zip_registry_files(self.registries):
            for _, entry in registry.items():
                if isinstance(entry, dict) and entry.get("local") is not None:
                    entry["local"] = _expand_registry_path(
                        registry_file, entry["local"]
                    )

        # Cleanup invalidities
        if self.writable:
            self.cleanup()
        else:
            # Just clean up loaded registries for internal use
            self._delete_invalid_registrations()

    def dump_registries(self) -> None:
        """
        Dump the plugin registries to their corresponding files, with some preprocessing beforehand.
        """
        # Cleanup invalidities
        self.cleanup()

        # Make 'local' entries relative to the registry file
        for registry_file, registry in _zip_registry_files(self.registries):
            for _, entry in registry.items():
                if entry["local"] is not None:
                    entry["local"] = str(
                        _expand_registry_path(
                            registry_file, entry["local"], collapse=True
                        )
                    )

        # Dump each registry to its corresponding file
        for registry_file, registry in _zip_registry_files(self.registries):
            dump_yaml(registry, registry_file)


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


@typecheck
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


@typecheck
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


@typecheck
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


@typecheck
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


@typecheck
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
    combined_registry = get_registries(
        home_registry=True, package_registry=True, combine=True
    )
    return set(combined_registry.keys())


@typecheck
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


@typecheck
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


class LocalPluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | str
    remote:  NotRequired[None | GitQuery]
    # fmt: on


class RemotePluginRegistryEntry(TypedDict):
    # fmt: off
    local:   NotRequired[None | str]
    remote:  None | GitQuery
    # fmt: on


@typecheck
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
            full_isinstance(entry, LocalPluginRegistryEntry)
            or full_isinstance(entry, RemotePluginRegistryEntry)
        ):
            debug_error(
                f"'entry' has an invalid structure. Expected (e):\n"
                f"{print_typed_dict_types(PluginRegistryEntry, indent=2, as_str=True)}"
                f"but got:\n{logger.pprint_dict(entry, indent=2, as_str=True)}"
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
            logger.error(
                f"package_registry: {package_registry}\n"
                f"plugin_name: {plugin_name}\n"
                f"registries: {registries}\n"
                f"registry_index: {registry_index}\n"
            )
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
                logger.error(
                    f"Removing plugin '{plugin_name}' from the {registry_str} registry 2."
                )
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
