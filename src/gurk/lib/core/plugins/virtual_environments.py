import shutil
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError, check_call
from venv import EnvBuilder

from gurk.lib.context import get_logger
from gurk.lib.utils import (
    GURK_VERSION,
    PACKAGE_SRC_PATH,
    PACKAGE_VENVS_PATH,
    typecheck,
)


@typecheck
def get_venv_dir(plugin_name: str) -> Path:
    """
    Get the path to the virtual environment directory for a plugin.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :return: Path to the virtual environment directory
    :rtype: Path
    """
    return PACKAGE_VENVS_PATH / plugin_name


@typecheck
def _get_venv_gurk_file(plugin_name: str) -> Path:
    """
    Get the path to the GURK version file for a plugin's virtual environment.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :return: Path to the GURK version file in the virtual environment
    :rtype: Path
    """
    return get_venv_dir(plugin_name) / "GURK_VERSION"


@typecheck
def venv_exists(venv_name: str) -> bool:
    """
    Check if a virtual environment exists for a plugin.

    :param venv_name: Name of the virtual environment (same as the plugin name)
    :type venv_name: str
    :return: True if the virtual environment exists, False otherwise
    :rtype: bool
    """
    return get_venv_dir(venv_name).is_dir()


@typecheck
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
    venv_dir = get_venv_dir(venv_name)
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
    except (KeyboardInterrupt, CalledProcessError) as e:
        logger.error(
            f"Failed to install dependencies for virtual environment '{venv_name}': {e}"
        )
        remove_venv(venv_name)
        return False

    # Write the gurk version to a file in the venv directory for later reference
    _get_venv_gurk_file(venv_name).write_text(GURK_VERSION + "\n")

    logger.success(
        f"Successfully created virtual environment for plugin '{venv_name}'"
    )
    return True


@typecheck
def remove_venv(venv_name: str) -> bool:
    """
    Remove the virtual environment for a plugin, if it exists.

    :param venv_name: Name of the virtual environment (same as the plugin name)
    :type venv_name: str
    :return: True if the virtual environment was removed successfully, False otherwise
    :rtype: bool
    """
    venv_path = get_venv_dir(venv_name)
    if venv_path.is_dir():
        try:
            shutil.rmtree(venv_path)
        except Exception:
            return False
        else:
            return True
    return False


@typecheck
def get_venv_gurk_version(venv_name: str) -> str | None:
    """
    Get the GURK version associated with a virtual environment.

    :param venv_name: Name of the virtual environment (same as the plugin name)
    :type venv_name: str
    :return: The GURK version if available, None otherwise
    :rtype: str | None
    """
    gurk_version_file = _get_venv_gurk_file(venv_name)
    if gurk_version_file.is_file():
        return gurk_version_file.read_text().strip()
    return None
