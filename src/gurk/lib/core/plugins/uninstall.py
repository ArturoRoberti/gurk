import shutil
from pathlib import Path

from gurk.lib.core.context import get_logger
from gurk.lib.core.context.registry_queries import (
    get_plugin_registration,
    update_registry,
)
from gurk.lib.core.plugins.virtual_environments import remove_venv

from .common import PluginSpecification


def remove_plugin(plugin: PluginSpecification, verbose: bool = False) -> None:
    """
    Remove a locally installed plugin.

    :param plugin: Name, PathLike, or GitQuery of the plugin to remove
    :type plugin: PluginSpecification
    :param verbose: Whether to print info messages
    :type verbose: bool
    :raises ModuleNotFoundError: If no such local plugin is found
    """
    # Get logger
    logger = get_logger()
    remove_msg = []

    # Get plugin data
    plugin_registration = get_plugin_registration(
        plugin, home_registry=True, package_registry=True, require_local=False
    )
    if not plugin_registration:
        raise ModuleNotFoundError(
            f"No installed plugin called '{plugin}' found"
        )
    plugin_name, plugin_entry = next(iter(plugin_registration.items()))

    # Remove plugin registry entry
    if update_registry(plugin_name, None):
        remove_msg.append("registry entry")

    # Remove plugin folder
    if plugin_entry["local"]:
        plugin_path = Path(plugin_entry["local"])
        if plugin_path.is_dir():
            shutil.rmtree(plugin_path)
        remove_msg.append("plugin files")

    # Remove plugin venv
    if remove_venv(plugin_name):
        remove_msg.append("virtual environment")

    if verbose:
        if remove_msg:
            logger.info(
                f"Successfully removed {' and '.join(remove_msg)} for plugin '{plugin_name}'"
            )
        else:
            logger.info(
                f"Nothing to remove for (package) plugin '{plugin_name}'"
            )
