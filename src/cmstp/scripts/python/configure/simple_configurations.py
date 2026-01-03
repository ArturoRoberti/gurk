import subprocess
from pathlib import Path
from shutil import copy2, copytree
from typing import Any, Dict, List

import commentjson
import requests

from cmstp.core.logger import Logger, LoggerSeverity
from cmstp.scripts.python.helpers._interface import get_config_args
from cmstp.scripts.python.helpers.processing import get_clean_lines
from cmstp.utils.common import resolve_package_path
from cmstp.utils.git_repos import clone_git_files, is_git_repo
from cmstp.utils.interface import bash_check, revert_sudo_permissions
from cmstp.utils.patterns import PatternCollection
from cmstp.utils.yaml import load_yaml


def configure_pinned_apps(*args: List[str]) -> None:
    """
    Configure pinned applications in the GNOME desktop environment.

    NOTE: Inexistent apps are stored as "pinned" but only actually pin after being installed.
          No error is raised by 'gsettings' if an app does not exist.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping configuration of pinned apps, as no task config file is provided",
            warning=True,
        )
        return

    # Get apps to pin
    apps = get_clean_lines(config_file)
    apps_str = "['" + "', '".join(apps) + "']"

    # (STEP) Pinning apps...
    subprocess.run(
        ["gsettings", "set", "org.gnome.shell", "favorite-apps", apps_str]
    )


# TODO: Expand any "[/].../.../..." paths to dicts. Pay attention not to merge with existing dicts.
def configure_filestructure(*args: List[str]) -> None:
    """
    Create a predefined file structure based on a YAML mapping.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, force, remaining_args = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping configuration of file structure, as no task config file is provided",
            warning=True,
        )
        return

    def recursive_create_structure(
        base_path: Path, structure: Dict[str, Any], overwrite: bool, sudo: bool
    ) -> None:
        for name, content in structure.items():
            dest_path = base_path / name
            if (content is None or isinstance(content, str)) and (
                dest_path.exists() and not overwrite
            ):
                Logger.step(
                    f"Path {dest_path} already exists. Skipping creation...",
                    warning=True,
                )
                continue

            if content is None:
                if Path(name).suffix:
                    # It's a file
                    dest_path.touch(exist_ok=True)
                else:
                    # It's a directory
                    dest_path.mkdir(exist_ok=True)
            elif isinstance(content, str):
                # Detect URL or symlink
                url_match = PatternCollection.PATH.patterns["url"].match(
                    content
                )
                symlink_match = PatternCollection.PATH.patterns[
                    "symlink"
                ].match(content)

                # Resolve package path (if applicable)
                content = resolve_package_path(
                    content if not symlink_match else symlink_match.group(1)
                )
                if content is None:
                    Logger.step(
                        f"Package resource in path '{content}' could not be resolved. Skipping...",
                        warning=True,
                    )
                    continue

                # Get content based on type
                if is_git_repo(content):
                    Logger.step(
                        f"Cloning git repository {content} into {dest_path}..."
                    )
                    # TODO: Optimize cloning for if the repo exists multiple times in the yaml. Maybe in general have tmpdir with all git repos and some caching?
                    cloned_path = clone_git_files(
                        content, dest_path, overwrite
                    )
                    if cloned_path is None:
                        Logger.step(
                            f"Failed to clone git repository {content}. Skipping...",
                            warning=True,
                        )
                        continue
                elif url_match:
                    Logger.step(
                        f"Downloading file from {content} to {dest_path}..."
                    )
                    response = requests.get(
                        content, timeout=60, headers={"Accept-Encoding": "*"}
                    )
                    if response.status_code == 200:
                        dest_path.write_bytes(response.content)
                    else:
                        Logger.step(
                            f"Failed to download file from {content}. HTTP status code: {response.status_code}",
                            warning=True,
                        )
                else:
                    # Assumed local path (possibly symlinked)
                    content = Path(content).expanduser()
                    if not content.exists():
                        Logger.step(
                            f"Source '{content}' does not exist. Skipping...",
                            warning=True,
                        )
                        continue

                    if symlink_match:
                        Logger.step(
                            f"Creating symlink from {content} to {dest_path}..."
                        )
                        dest_path.symlink_to(content)
                    else:
                        Logger.step(
                            f"Copying from local path {content} to {dest_path}..."
                        )
                        if content.is_file():
                            copy2(content, dest_path)
                        elif content.is_dir():
                            copytree(content, dest_path, dirs_exist_ok=True)
            elif isinstance(content, dict):
                # It's a directory with further contents
                dest_path.mkdir(exist_ok=True)
                recursive_create_structure(dest_path, content, overwrite, sudo)
            else:
                Logger.step(
                    f"Unsupported entry type '{type(content)}' for {content}. Skipping...",
                    warning=True,
                )

            # Revert to user permissions if under HOME directory
            if not sudo:
                revert_sudo_permissions(dest_path)

    # Check file structure
    config_data = load_yaml(config_file)
    if config_data is None:
        Logger.logrichprint(
            LoggerSeverity.FATAL,
            f"Invalid YAML file provided for file structure configuration: {config_file}",
        )
        raise ValueError

    # (STEP) Creating file structure...
    if config_data.get("HOME"):
        recursive_create_structure(
            Path.home(),
            config_data["HOME"],
            force,
            False,
        )
    if config_data.get("ROOT"):
        if "--root" not in remaining_args:
            Logger.logrichprint(
                LoggerSeverity.WARNING,
                "Skipping root (/) file structure configuration, as '--root' flag is not provided.",
            )
        else:
            recursive_create_structure(
                Path("/"), config_data["ROOT"], False, True
            )


def configure_vscode_keybindings(*args: List[str]) -> None:
    """
    Configure VSCode keybindings.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping configuration of VSCode keybindings, as no task config file is provided",
            warning=True,
        )
        return

    # Check VSCode installation
    result = bash_check("check_install_vscode")
    if not result.returncode == 0:
        Logger.logrichprint(
            LoggerSeverity.FATAL,
            "VSCode is not installed. Please install VSCode before configuring keybindings.",
        )
        raise EnvironmentError

    # Ensure VSCode keybindings file exists
    vscode_keys = Path.home() / ".config/Code/User/keybindings.json"
    vscode_keys.parent.mkdir(parents=True, exist_ok=True)
    if not vscode_keys.exists():
        Logger.logrichprint(
            LoggerSeverity.WARNING,
            "VSCode keybindings file does not exist, creating an empty one.",
        )
        vscode_keys.write_text("[]", encoding="utf-8")

    # Load both JSON files (supporting comments)
    existing = commentjson.load(vscode_keys.open("r", encoding="utf-8"))
    new_keys = commentjson.load(config_file.open("r", encoding="utf-8"))

    # Merge arrays like jq -s '.[0] + .[1]'
    merged = existing + new_keys

    # Write merged file back
    vscode_keys.write_text(
        commentjson.dumps(merged, indent=2), encoding="utf-8"
    )
    Logger.step("VSCode keybindings configured successfully.")
