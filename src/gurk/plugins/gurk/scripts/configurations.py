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

import os
import subprocess
from contextlib import nullcontext
from functools import cache
from pathlib import Path
from shutil import copy2, copytree
from typing import Any

import requests

from gurk import (
    LoggerSeverity,
    PatternCollection,
    UserContext,
    get_clean_lines,
    getent_passwd,
    git_clone,
    is_git_repo,
    is_url,
    load_yaml,
    log_step,
    logrichprint,
    overlay_dicts,
    parse_task_args,
    resolve_package_path,
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


def configure_filestructure(*args: list[str]) -> None:
    """
    Create a predefined file structure based on a YAML mapping.
    """
    # Parse task args
    task_args = parse_task_args(args)

    @cache
    def _expanduser(key: str) -> str:
        """
        Expand '~' at the start of the given key to the actual home directory of the user.

        :param key: The string key to expand
        :type key: str
        :return: The key with ~ expanded to the user's home directory
        :rtype: str
        """
        if key == "~" or key.startswith("~/"):
            sudo_user = os.environ.get("SUDO_USER")
            home = (
                getent_passwd(sudo_user, "home")
                if sudo_user
                else os.path.expanduser("~")
            )
            key = home + key[1:]
        return key

    def expand_paths_to_dicts(dct: dict, _toplevel: bool = True) -> dict:
        """
        Recursively expand path-like string keys into nested dicts, then merge them.

        :param dct: Dictionary with path-like keys to expand.
        :type dct: dict
        :return: A single merged nested dictionary.
        :rtype: dict
        """
        expanded = []
        for key, value in dct.items():
            # Filter out keys that don't match the expected path type for this level
            is_absolute = key.startswith("/") or key.startswith("~")
            if _toplevel:
                if not is_absolute:
                    log_step(
                        f"Skipping top-level key {key!r} (not a "
                        "required absolute path or '~' expansion)",
                        warning=True,
                    )
                    continue
                elif key == "/":
                    log_step(
                        f"Skipping top-level key {key!r} (unallowed "
                        "root path key without subpaths)",
                        warning=True,
                    )
                    continue
                elif (
                    not task_args.gurk_configure_root_filestructure
                    and not _expanduser(key).startswith(_expanduser("~"))
                ):
                    log_step(
                        f"Skipping non-home-level key {key!r}. Pass "
                        "'--gurk-configure-root-filestructure' flag "
                        "to allow non-home-level configuration.",
                        warning=True,
                    )
                    continue
            elif is_absolute:
                log_step(
                    f"Skipping nested key {key!r} (unallowed "
                    "absolute path or '~' expansion)",
                    warning=True,
                )
                continue

            # Recurse into dict values before processing this key
            if isinstance(value, dict):
                value = expand_paths_to_dicts(value, _toplevel=False)

            # Resolve ~ to the actual home directory
            key = _expanduser(key)

            # Split the path into parts, dropping empty segments from leading/trailing slashes
            parts = [p for p in key.split("/") if p]
            # Restore the leading '/' on the first part for absolute paths
            if key.startswith("/") and parts:
                parts[0] = "/" + parts[0]

            # Wrap the value in nested dicts, one per path part (innermost first)
            nested = value
            for part in reversed(parts):
                nested = {part: nested}
            expanded.append(nested)

        return overlay_dicts(expanded)

    def recursive_create_structure(
        base_path: Path, structure: dict[str, Any], overwrite: bool
    ) -> None:
        """
        Recursively create the file structure defined in the given dictionary.

        :param base_path: The base path to create the structure in
        :type base_path: Path
        :param structure: A dictionary defining the file structure to create
        :type structure: dict[str, Any]
        :param overwrite: Whether to overwrite existing files/directories
        :type overwrite: bool
        """
        for name, content in structure.items():
            dest_path = base_path / name
            dest_is_under_home = dest_path.as_posix().startswith(
                _expanduser("~")
            )
            if dest_is_under_home:
                ctx = UserContext()
            else:
                ctx = nullcontext()

            if content is None:
                with ctx:
                    if Path(name).suffix:
                        # It's a file
                        dest_path.touch(exist_ok=True)
                    else:
                        # It's a directory
                        dest_path.mkdir(exist_ok=True)
            elif isinstance(content, str):
                # Handle an existing destination
                if dest_path.exists():
                    if not task_args.force:
                        log_step(
                            f"Destination {dest_path} already exists. Use "
                            "'--force' to overwrite it. Skipping creation...",
                            warning=True,
                        )
                        continue
                    elif not dest_is_under_home:
                        log_step(
                            f"Destination {dest_path} already exists and overwriting outside "
                            "the home directory is not allowed. Skipping creation...",
                            warning=True,
                        )
                        continue

                # Detect symlink
                symlink_match = PatternCollection.PATH.patterns[
                    "symlink"
                ].match(content)

                # Resolve package path (if applicable)
                content = resolve_package_path(
                    content
                    if symlink_match is None
                    else symlink_match.group(1)
                )
                if content is None:
                    log_step(
                        f"Package resource in path '{content}' could not be resolved. Skipping...",
                        warning=True,
                    )
                    continue

                # Get content based on type
                with ctx:
                    if is_git_repo(content):
                        log_step(
                            f"Cloning git repository {content} into {dest_path}..."
                        )
                        try:
                            git_clone(content, dest_path, task_args.force)
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
                            content,
                            timeout=60,
                            headers={"Accept-Encoding": "*"},
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
                        content = Path(_expanduser(content))
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
                                copytree(
                                    content, dest_path, dirs_exist_ok=True
                                )
            elif isinstance(content, dict):
                # It's a directory with further contents
                with ctx:
                    dest_path.mkdir(exist_ok=True)
                recursive_create_structure(dest_path, content, overwrite)
            else:
                log_step(
                    f"Unsupported entry type '{type(content).__name__}' for {content}. Skipping...",
                    warning=True,
                )

    # Check file structure
    config_data = load_yaml(task_args.config_file)
    if config_data is None:
        logrichprint(
            LoggerSeverity.FATAL,
            f"Invalid YAML file provided for file structure configuration: {task_args.config_file}",
        )
        raise ValueError

    # Expand path-like keys to dicts
    config_data = expand_paths_to_dicts(config_data)

    # (STEP) Creating file structure...
    recursive_create_structure(
        Path("/"),
        config_data,
        task_args.force,
    )
