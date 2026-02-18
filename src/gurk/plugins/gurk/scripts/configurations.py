import subprocess
from pathlib import Path
from shutil import copy2, copytree
from typing import Any

import requests

from gurk import (
    LoggerSeverity,
    PatternCollection,
    get_clean_lines,
    git_clone,
    is_git_repo,
    is_url,
    load_yaml,
    log_step,
    logrichprint,
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
#       This could also be used together with getent_passwd(os.getenv("SUDO_USER"), "home")
#           to ge the home directory of the user and thus remove the need to use HOME and ROOT.
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
                log_step(
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
                    log_step(
                        f"Package resource in path '{content}' could not be resolved. Skipping...",
                        warning=True,
                    )
                    continue

                # Get content based on type
                if is_git_repo(content):
                    log_step(
                        f"Cloning git repository {content} into {dest_path}..."
                    )
                    try:
                        git_clone(content, dest_path, overwrite)
                    except subprocess.CalledProcessError:
                        log_step(
                            f"Failed to clone git repository {content}. Skipping...",
                            warning=True,
                        )
                        continue
                elif is_url(content):
                    log_step(
                        f"Downloading file from {content} to {dest_path}..."
                    )
                    response = requests.get(
                        content, timeout=60, headers={"Accept-Encoding": "*"}
                    )
                    if response.status_code == 200:
                        dest_path.write_bytes(response.content)
                    else:
                        log_step(
                            f"Failed to download file from {content}. HTTP status code: {response.status_code}",
                            warning=True,
                        )
                else:
                    # Assumed local path (possibly symlinked)
                    content = Path(
                        content
                    ).expanduser()  # TODO: Does this work when this is working in privileged mode?
                    ## Absolute path
                    if content.is_absolute():
                        pass
                    ## Relative path (to base path)
                    elif str(content).startswith("./"):
                        content = (base_path / content).resolve()
                    ## Relative path (to config file)
                    else:
                        content = (
                            task_args.config_file.parent / content
                        ).resolve()

                    if not content.exists():
                        log_step(
                            f"Source '{content}' does not exist. Skipping...",
                            warning=True,
                        )
                        continue

                    if symlink_match:
                        log_step(
                            f"Creating symlink from {content} to {dest_path}..."
                        )
                        dest_path.symlink_to(content)
                    else:
                        log_step(
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
                log_step(
                    f"Unsupported entry type '{type(content).__name__}' for {content}. Skipping...",
                    warning=True,
                )

            # Revert to user permissions if under HOME directory
            if not sudo:
                revert_sudo_permissions(dest_path)

    # Check file structure
    config_data = load_yaml(task_args.config_file)
    if config_data is None:
        logrichprint(
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
        if not task_args.gurk_configure_root_filestructure:
            logrichprint(
                LoggerSeverity.WARNING,
                "Skipping root (/) file structure configuration, as "
                "'--gurk-configure-root-filestructure' flag is not provided.",
            )
        else:
            recursive_create_structure(
                Path("/"), config_data["ROOT"], False, True
            )
