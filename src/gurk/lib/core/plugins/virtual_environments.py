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

import shutil
import subprocess
from pathlib import Path
from venv import EnvBuilder

from gurk.lib.context import get_logger
from gurk.lib.utils import (
    EDITABLE_INSTALL,
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
    pip_bin = (venv_dir / "bin" / "pip").as_posix()
    all_dependencies = dependencies + (
        [
            "-e",
            PACKAGE_SRC_PATH.parents[1].as_posix(),
        ]
        if EDITABLE_INSTALL
        else [f"gurk=={GURK_VERSION}"]
    )
    try:
        subprocess.check_call(
            [pip_bin, "install", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL,
        )
        subprocess.check_call(
            [pip_bin, "install", *all_dependencies],
            stdout=subprocess.DEVNULL,
        )
    except (KeyboardInterrupt, subprocess.CalledProcessError) as e:
        logger.error(
            f"Failed to install dependencies for virtual environment '{venv_name}': {e}"
        )
        remove_venv(venv_name)
        return False

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
def get_venv_package_version(venv_name: str, package_name: str) -> str | None:
    """
    Get the version of a specific package associated with a virtual environment.

    :param venv_name: Name of the virtual environment (same as the plugin name)
    :type venv_name: str
    :param package_name: Name of the package to get the version for
    :type package_name: str
    :return: The package version if available, None otherwise
    :rtype: str | None
    """
    python_bin = (get_venv_dir(venv_name) / "bin" / "python").as_posix()
    try:
        return subprocess.run(
            [
                python_bin,
                "-c",
                f"from importlib.metadata import version; print(version('{package_name}'))",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return None
