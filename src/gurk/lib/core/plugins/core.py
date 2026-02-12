from gurk.lib.core.context import get_logger
from gurk.lib.core.context.registry_queries import is_plugin_registered
from gurk.lib.core.plugins.virtual_environments import venv_exists

from .common import PluginSpecification
from .getters import get_plugin_data


def is_plugin_installed(
    plugin: PluginSpecification, *, require_venv: bool = True
) -> bool:
    """
    Check if a plugin is validly installed, optionally requiring that its venv exists.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :param require_venv: Whether to check if the plugin's virtual environment exists
    :type require_venv: bool
    :return: True if the plugin is installed (and its venv exists if require_venv is True), False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check that the plugin is validly installed
    try:
        plugin_data = get_plugin_data(plugin)
    except ModuleNotFoundError as e:
        if is_plugin_registered(
            plugin, home_registry=True, package_registry=True
        ):
            logger.debug(
                f"Plugin '{plugin}' is installed but invalid ({e}) - please fix or remove it"
            )
        else:
            logger.debug(f"Plugin '{plugin}' is not installed.")
        return False

    # Check that the plugin venv exists
    if require_venv and not venv_exists(plugin_data["metadata"]["name"]):
        logger.debug(
            f"Plugin '{plugin}' is installed but its venv is missing."
        )
        return False

    return True
