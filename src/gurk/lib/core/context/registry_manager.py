from __future__ import annotations

import shutil
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
from typing import TypeAlias

from gurk.lib.utils.common import (
    PACKAGE_HOME_PATH,
    PACKAGE_SRC_PATH,
    PACKAGE_VENVS_PATH,
    PathLike,
)
from gurk.lib.utils.configs import dump_yaml, load_yaml, overlay_dicts
from gurk.lib.utils.remotes import is_git_repo
from gurk.lib.utils.typed_dict import validate_typed_dict

from .logger import get_logger
from .registry_types import (
    PluginRegistry,
    PluginRegistryEntry,
    _deepcopy_tuple,
)


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

    @staticmethod
    def is_entry_valid(
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
            "Entry must conform to PluginRegistryEntry schema": validate_typed_dict(
                entry, PluginRegistryEntry
            ),
            "Entry must define at least one of 'local' or 'remote'": any(
                (entry.get("local"), entry.get("remote"))
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
                if not self.is_entry_valid(name, entry, registry_file):
                    local_msg = "local path of " if is_package_registry else ""
                    warn_msg = (
                        f"Removing {local_msg}invalid plugin registry entry "
                        f"'{name}' from {registry_file.as_posix()}."
                    )
                    if not is_package_registry:
                        logger.warning(warn_msg)
                        del registry[name]
                    elif (
                        validate_typed_dict(entry, PluginRegistryEntry)
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

        # Cleanup invalidities
        if self.writable:
            self.cleanup()
        else:
            # Just clean up loaded registries for internal use
            self._delete_invalid_registrations()

        # Prepend registry path to 'local' entries
        for registry_file, registry in _zip_registry_files(self.registries):
            for _, entry in registry.items():
                if entry["local"] is not None:
                    entry["local"] = str(
                        _expand_registry_path(registry_file, entry["local"])
                    )  # NOTE: Could use Path here instead of str — would require PluginRegistryEntry changes

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
