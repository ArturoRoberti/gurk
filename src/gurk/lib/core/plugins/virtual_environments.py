import shutil
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError, check_call
from venv import EnvBuilder

from gurk.lib.core.context import get_logger
from gurk.lib.utils.common import PACKAGE_SRC_PATH, PACKAGE_VENVS_PATH


def _get_venv_dir(plugin_name: str) -> Path:
    """
    Get the path to the virtual environment directory for a plugin.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :return: Path to the virtual environment directory
    :rtype: Path
    """
    return PACKAGE_VENVS_PATH / plugin_name


def venv_exists(venv_name: str) -> bool:
    """
    Check if a virtual environment exists for a plugin.

    :param venv_name: Name of the virtual environment (same as the plugin name)
    :type venv_name: str
    :return: True if the virtual environment exists, False otherwise
    :rtype: bool
    """
    return _get_venv_dir(venv_name).is_dir()


def create_venv(venv_name: str, dependencies: list[str]) -> bool:
    """
    Create a virtual environment for a plugin and install its dependencies.

    :param venv_name: Name of the virtual environment (same as the plugin name)
    :type venv_name: str
    :param dependencies: List of dependencies to install
    :type dependencies: list[str]
    :return: True if the virtual environment was created successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check if venv already exists
    venv_dir = _get_venv_dir(venv_name)
    if venv_exists(venv_name):
        logger.error(
            f"Virtual environment for plugin '{venv_name}' already exists at {venv_dir}"
        )
        return False

    # Create venv
    dependencies_str = (
        ("\n- " + "\n- ".join(dependencies)) if dependencies else " None"
    )
    logger.info(
        f"Creating virtual environment for plugin '{venv_name}' "
        f"in {venv_dir} with dependencies:{dependencies_str}"
    )
    EnvBuilder(with_pip=True).create(venv_dir)

    # Install dependencies
    pip_bin = str(venv_dir / "bin" / "pip")
    all_dependencies = dependencies + [PACKAGE_SRC_PATH.parents[1].as_posix()]
    try:
        check_call([pip_bin, "install", "--upgrade", "pip"], stdout=DEVNULL)
        check_call([pip_bin, "install", *all_dependencies], stdout=DEVNULL)
    except CalledProcessError as e:
        logger.error(
            f"Failed to install dependencies for virtual environment '{venv_name}': {e}"
        )
        return False

    logger.info(
        f"Successfully created virtual environment for plugin '{venv_name}'"
    )
    return True


def remove_venv(venv_name: str) -> bool:
    """
    Remove the virtual environment for a plugin, if it exists.

    :param venv_name: Name of the virtual environment (same as the plugin name)
    :type venv_name: str
    :return: True if the virtual environment was removed successfully, False otherwise
    :rtype: bool
    """
    venv_path = _get_venv_dir(venv_name)
    if venv_path.is_dir():
        try:
            shutil.rmtree(venv_path)
        except Exception:
            return False
        else:
            return True
    return False
