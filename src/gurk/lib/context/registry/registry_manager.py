import shutil
from contextvars import ContextVar
from copy import deepcopy

from gurk.lib.shared.configs import dump_yaml, load_yaml
from gurk.lib.shared.plugins import (
    PluginRegistry,
    ResolvedPluginRegistry,
    ResolvedPluginRegistryEntry,
)
from gurk.lib.utils import PACKAGE_VENVS_PATH, full_isinstance, overlay_dicts

from ..logger import get_logger
from .registry_utils import (
    _deepcopy_tuple,
    _expand_registry_path,
    _get_registry_files,
    _is_entry_valid,
    _zip_registry_files,
    get_plugin_directories,
)

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
        """Delete invalid plugin registry entries from the given registries."""
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
                        full_isinstance(entry, ResolvedPluginRegistryEntry)
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
        """Remove any plugin directories that are not registered in the currently active registrator's plugin registry."""
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

    def load_registries(
        self,
    ) -> tuple[ResolvedPluginRegistry, ResolvedPluginRegistry]:
        """
        Load the plugin registries from their corresponding files, validating their structure and prepending the path to local entries.

        :return: Tuple of plugin registries (home, package)
        :rtype: tuple[ResolvedPluginRegistry, ResolvedPluginRegistry]
        """
        # Load registry files
        self.registries: tuple[PluginRegistry, PluginRegistry] = tuple(
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


def _get_registries() -> tuple[ResolvedPluginRegistry, ResolvedPluginRegistry]:
    """
    Get the currently active registrator's plugin registries without deepcopying
    them (for internal use only). Also deletes invalid entries before returning.

    :return: Tuple of plugin registries (home, package)
    :rtype: tuple[ResolvedPluginRegistry, ResolvedPluginRegistry]
    :raises RuntimeError: If no registrator is initialized
    """
    registries = _current_registries.get()
    if registries is None:
        raise RuntimeError("RegistryManager not initialized")

    return registries
