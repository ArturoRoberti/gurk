#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

import tomli_w
from packaging.version import Version

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from utils import DEFAULT_BRANCH, get_changed_plugin_folders


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
        tomli_w.dump(data, f)


def _check_toml_version(file: Path) -> bool:
    """
    Check if the version in the given TOML file is greater than or equal to
    the version in the main branch.

    :param file: Path to the TOML file
    :type file: Path
    :return: True if the version is greater than or equal to main branch version, False otherwise
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
    if current_version >= main_version:
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


def main():
    # Bump main pyproject.toml version, if necessary
    version_file = Path(__file__).parents[2] / "pyproject.toml"
    bump_toml_version_if_necessary(version_file)

    # Bump local plugin versions, if necessary
    changed_plugins = get_changed_plugin_folders()
    for plugin_path in changed_plugins:
        plugin_version_file = plugin_path / "pyproject.toml"
        bump_toml_version_if_necessary(plugin_version_file)


if __name__ == "__main__":
    main()
