#!/usr/bin/env python3

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

import subprocess
import sys
from pathlib import Path

import tomli_w
from packaging.version import Version

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from utils import DEFAULT_BRANCH, PLUGIN_FOLDER_PREFIX, REPO_ROOT, get_git_diff


def load_toml(path: Path) -> dict:
    """
    Load a TOML file.

    :param path: Path to the TOML file
    :type path: Path
    """
    with path.open("rb") as f:
        return tomllib.load(f)


def save_toml(data: dict, path: Path) -> None:
    """
    Save data to a TOML file.

    :param data: Data to save
    :type data: dict
    :param path: Path to the TOML file
    :type path: Path
    """
    with path.open("wb") as f:
        tomli_w.dump(data, f, indent=2)


def _check_toml_version(file: Path) -> bool:
    """
    Check if the version in the given TOML file is greater than the version in the main branch.

    :param file: Path to the TOML file
    :type file: Path
    :return: True if the version is greater than the main branch version, False otherwise
    :rtype: bool
    """
    # Get current version
    try:
        current_version = Version(load_toml(file)["project"]["version"])
    except Exception:
        return False  # No valid version found, cannot compare

    # Get main branch version
    try:
        content = subprocess.check_output(
            ["git", "show", f"{DEFAULT_BRANCH}:{file}"],
            text=True,
        )
        main_version = Version(tomllib.loads(content)["project"]["version"])
    except Exception:
        return True  # Does not exist in main, consider it new

    # Compare versions
    if current_version > main_version:
        return True
    else:
        return False


def _bump_toml_version(file: Path) -> None:
    """
    Bump the version in the given TOML file by incrementing the patch number.

    :param file: Path to the TOML file
    :type file: Path
    """
    # Get current version
    try:
        data = load_toml(file)
        version = Version(data["project"]["version"])
    except Exception:
        return False  # No valid version found

    # Bump version
    new_version = Version(
        f"{version.major}.{version.minor}.{version.micro + 1}"
    )
    data["project"]["version"] = str(new_version)
    save_toml(data, file)


def bump_toml_version_if_necessary(file: Path) -> None:
    """
    Bump the version in the given TOML file if it is not greater than or equal to
    the version in the main branch.

    :param file: Path to the TOML file
    :type file: Path
    """
    if not _check_toml_version(file):
        _bump_toml_version(file)


def _get_changed_plugin_folder_names() -> set[str]:
    """
    Get the set of changed plugin folder names under PLUGIN_FOLDER_PREFIX.

    :return: Set of changed plugin folder names
    :rtype: set[str]
    """
    # Get list of changed files under PLUGIN_FOLDER_PREFIX
    diff_output = get_git_diff(PLUGIN_FOLDER_PREFIX, name_only=True).strip()
    if not diff_output:
        return set()

    # Extract unique plugin folder names
    plugins = set()
    for path in diff_output.splitlines():
        if not path.startswith(PLUGIN_FOLDER_PREFIX):
            continue

        remainder = path[len(PLUGIN_FOLDER_PREFIX) :]
        parts = remainder.split("/", 1)

        if len(parts) > 1 and parts[0] != "gurk":
            plugins.add(parts[0])

    # Return prefixed with PLUGIN_FOLDER_PREFIX
    return plugins


def get_changed_plugin_folders() -> set[Path]:
    """
    Get the set of changed plugin folders under PLUGIN_FOLDER_PREFIX.

    :return: Set of changed plugin folder paths
    :rtype: set[Path]
    """
    return {
        Path(PLUGIN_FOLDER_PREFIX) / p
        for p in _get_changed_plugin_folder_names()
    }


def main():
    # Bump main pyproject.toml version, if necessary
    GURK_METADATA_FILENAME = "pyproject.toml"
    version_file = (
        Path(__file__).parents[2] / GURK_METADATA_FILENAME
    ).relative_to(REPO_ROOT)
    bump_toml_version_if_necessary(version_file)

    # Bump local plugin versions, if necessary
    changed_plugins = get_changed_plugin_folders()
    for plugin_path in changed_plugins:
        plugin_version_file = plugin_path / GURK_METADATA_FILENAME
        bump_toml_version_if_necessary(plugin_version_file)


if __name__ == "__main__":
    main()
