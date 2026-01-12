import subprocess
from pathlib import Path
from shutil import copy2, copytree
from typing import Any

import requests

from gurk import (
    Logger,
    LoggerSeverity,
    PatternCollection,
    clone_git_files,
    get_clean_lines,
    is_git_repo,
    is_url,
    load_yaml,
    parse_task_args,
    resolve_package_path,
    revert_sudo_permissions,
)


def configure_pinned_apps(*args: list[str]) -> None:
    """
    Configure pinned applications in the GNOME desktop environment.

    NOTE: Inexistent apps are stored as "pinned" but only actually pin after being installed.
          No error is raised by 'gsettings' if an app does not exist.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # Get apps to pin
    apps = get_clean_lines(task_args.config_file)
    apps_str = "['" + "', '".join(apps) + "']"

    # (STEP) Pinning apps...
    subprocess.run(
        ["gsettings", "set", "org.gnome.shell", "favorite-apps", apps_str]
    )


# TODO: Expand any "[/].../.../..." paths to dicts. Pay attention not to merge with existing dicts.
def configure_filestructure(*args: list[str]) -> None:
    """
    Create a predefined file structure based on a YAML mapping.
    """
    # Parse task args
    task_args = parse_task_args(args)

    def recursive_create_structure(
        base_path: Path, structure: dict[str, Any], overwrite: bool, sudo: bool
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
                # Detect symlink
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
                    cloned_path = clone_git_files(
                        content, dest_path, overwrite
                    )
                    if cloned_path is None:
                        Logger.step(
                            f"Failed to clone git repository {content}. Skipping...",
                            warning=True,
                        )
                        continue
                elif is_url(content):
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
    config_data = load_yaml(task_args.config_file)
    if config_data is None:
        Logger.logrichprint(
            LoggerSeverity.FATAL,
            f"Invalid YAML file provided for file structure configuration: {task_args.config_file}",
        )
        raise ValueError

    # (STEP) Creating file structure...
    if config_data.get("HOME"):
        recursive_create_structure(
            Path.home(),
            config_data["HOME"],
            task_args.force,
            False,
        )
    if config_data.get("ROOT"):
        if not task_args.root:
            Logger.logrichprint(
                LoggerSeverity.WARNING,
                "Skipping root (/) file structure configuration, as '--root' flag is not provided.",
            )
        else:
            recursive_create_structure(
                Path("/"), config_data["ROOT"], False, True
            )
