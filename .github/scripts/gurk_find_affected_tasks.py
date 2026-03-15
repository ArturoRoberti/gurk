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

try:
    from gurk.lib.context import GurkContext, get_plugin_directories
    from gurk.lib.core.plugins import (
        get_available_plugin_tasks,
        install_plugin,
        iter_configs,
        iter_scripts,
    )
    from gurk.lib.shared.configs import load_yaml
    from gurk.lib.shared.remotes import get_commit_timestamp
    from gurk.lib.shared.scripts import ScriptBlockTypes, get_block_spans
    from gurk.lib.utils import RUNNER_SPECIFIC_TASKS
except ImportError:
    raise ImportError(
        "The gurk package needs to be installed to run this script."
    )

import os
import re
import subprocess
from pathlib import Path
from typing import TypeAlias
from urllib.parse import parse_qs, urlparse

import networkx as nx
from utils import DEFAULT_BRANCH, PLUGIN_FOLDER_PREFIX, REPO_ROOT, get_git_diff


def _get_changed_remote_plugin_sources() -> set[str]:
    """
    Get the set of changed or new remote plugin sources under PLUGIN_FOLDER_PREFIX.

    :return: Set of changed or new remote plugin sources
    :rtype: set[str]
    """
    RegistryData: TypeAlias = dict[str, dict[str, str]]

    def filter_remote_plugins(registry_data: RegistryData) -> RegistryData:
        return {
            k: v
            for k, v in registry_data.items()
            if v.get("local") is None and v.get("remote") is not None
        }

    # Load current registry.yaml
    registry_path = REPO_ROOT / PLUGIN_FOLDER_PREFIX / "registry.yaml"
    curr_registry_data = load_yaml(registry_path)
    curr_registry_data = filter_remote_plugins(curr_registry_data)

    # Load default branch registry.yaml
    default_registry = subprocess.check_output(
        [
            "git",
            "show",
            f"{DEFAULT_BRANCH}:{registry_path.relative_to(REPO_ROOT)}",
        ],
        text=True,
    )
    default_registry_data = load_yaml(default_registry, from_str=True)
    default_registry_data = filter_remote_plugins(default_registry_data)

    # Get new remote plugins
    new_plugins = {
        v["remote"]
        for k, v in curr_registry_data.items()
        if k not in default_registry_data
    }

    # Get changed remote plugins
    changed_plugins = set()
    for k, v in curr_registry_data.items():
        if k not in default_registry_data:
            continue  # New plugin, already handled

        # Get current commit
        parts = urlparse(v["remote"])
        query = parse_qs(parts.query)
        t_commit = get_commit_timestamp(query["url"], query["commit"])

        # Get default branch commit
        parts_def = urlparse(default_registry_data[k]["remote"])
        query_def = parse_qs(parts_def.query)
        t_commit_def = get_commit_timestamp(
            query_def["url"], query_def["commit"]
        )

        # Compare commit timestamps
        if t_commit > t_commit_def:
            changed_plugins.add(v["remote"])
        elif t_commit < t_commit_def:
            raise RuntimeError(
                f"Plugin '{k}' has an older commit timestamp ({t_commit}) than in the default branch ({t_commit_def})."
            )

    return new_plugins.union(changed_plugins)


def _parse_diff_changed_lines(diff_text: str) -> dict[str, set[int]]:
    """
    Parse a unified diff text and return a mapping of file paths to changed line numbers.
        :NOTE: This currently also counts changed comments and blank lines.

    :param diff_text: The unified diff text
    :type diff_text: str
    :return: Mapping of file paths to sets of changed line numbers
    :rtype: dict[str, set[int]]
    """
    changed: dict[str, set[int]] = {}
    current_file = None
    hunk_re = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    file_re = re.compile(r"^\+\+\+ b/(.+)$")

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            m = file_re.match(line)
            if m:
                current_file = m.group(1)
                changed.setdefault(current_file, set())
        elif line.startswith("@@") and current_file:
            m = hunk_re.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2) or "1")
                for line_number in range(start, start + count):
                    changed[current_file].add(line_number)

    # Prepend repo root to file paths
    return {
        Path(k).relative_to(PLUGIN_FOLDER_PREFIX).as_posix(): v
        for k, v in changed.items()
    }


def _affected_blocks(path: Path, changed_lines: set[int]) -> set[str]:
    """
    Determine which top-level blocks (functions/entrypoint) are affected by the changed lines.
        :NOTE: Assumes scripts are valid, i.e. only contain functions and an entrypoint (and imports for Python)

    :param path: Path to the script file
    :type path: Path
    :param changed_lines: Set of changed line numbers in the script
    :type changed_lines: set[int]
    :return: Set of affected block names (function names or None for entrypoint)
    :rtype: set[str]
    """
    affected_blocks = set()
    blocks = [
        b
        for b in get_block_spans(path)
        if b["type"]
        in {ScriptBlockTypes.FUNCTION, ScriptBlockTypes.ENTRYPOINT}
    ]
    for block in blocks:
        lines = set(range(block["lines"][0], block["lines"][1] + 1))
        if lines & changed_lines:
            affected_blocks.add(block["name"])

    return affected_blocks


def compute_affected_tasks() -> list[str]:
    """
    Compute the set of affected tasks based on the git diff.

    :return: Set of affected task names
    :rtype: set[str]
    """
    # Parse diff to get changed line numbers per file
    diff_text = get_git_diff(PLUGIN_FOLDER_PREFIX, staged=True)
    changed_lines_map = _parse_diff_changed_lines(diff_text)

    # Find affected script blocks (functions/entrypoints)
    pkg_plugin_dir = get_plugin_directories(public=False, private=True)
    affected_script_blocks: dict[Path, set[str]] = {}
    for file_path in iter_scripts():
        affected_script_blocks[file_path] = _affected_blocks(
            file_path,
            changed_lines_map.get(
                file_path.relative_to(pkg_plugin_dir).as_posix(),
                set(),
            ),
        )

    # Find affected config files
    affected_config_files = set()
    for file_path in iter_configs():
        if (
            file_path.relative_to(pkg_plugin_dir).as_posix()
            in changed_lines_map
        ):
            affected_config_files.add(file_path.name)

    # Determine affected tasks
    tasks = get_available_plugin_tasks()
    affected_tasks: set[str] = set()
    for task_name, task in tasks.items():
        # Affected script block
        script = task["script"]
        if script in affected_script_blocks:
            affected_blocks = affected_script_blocks[script]
            if task["function"] in affected_blocks:
                # NOTE: Includes entrypoint (None)
                affected_tasks.add(task_name)
                continue

        # Affected config file
        config_file = task["config_file"]
        if config_file and config_file in affected_config_files:
            affected_tasks.add(task_name)
            continue

    # Filter out runner-specific tasks # TODO: Handle and/or fix these instead
    affected_tasks -= set(RUNNER_SPECIFIC_TASKS)

    # Filter out task who run as dependencies of other affected tasks
    ## Build dependency graph
    task_graph = nx.DiGraph()
    for task_name, task in tasks.items():
        task_graph.add_node(task_name)
        for dep in task["depends_on"]:
            task_graph.add_edge(dep, task_name)
    ## Filter dependencies
    dependency_tasks = set()
    for task in affected_tasks:
        descendants = nx.descendants(task_graph, task)
        if descendants.intersection(affected_tasks):
            dependency_tasks.add(task)
    affected_tasks -= dependency_tasks

    # Return affected tasks - run "uninstall" tasks first to free runner space
    uninstall_tasks = {t for t in affected_tasks if t.startswith("uninstall")}
    return sorted(uninstall_tasks) + sorted(affected_tasks - uninstall_tasks)


if __name__ == "__main__":
    # Pull changed remote plugins and stage for diff analysis
    changed_remote_plugins = _get_changed_remote_plugin_sources()
    for plugin_source in changed_remote_plugins:
        if not install_plugin(plugin_source):
            raise RuntimeError(
                f"Failed to pull changed/new remote plugin from source '{plugin_source}'."
            )
    if changed_remote_plugins:
        subprocess.run(
            ["git", "add", PLUGIN_FOLDER_PREFIX],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
        )

    # Compute affected tasks from git diff
    with GurkContext(logger=None, writable=False):
        affected_tasks = compute_affected_tasks()

    # Write to GitHub Actions env
    github_env = os.environ.get("GITHUB_ENV")
    if github_env and affected_tasks:
        with open(github_env, "a") as f:
            f.write(f"AFFECTED_TASKS={','.join(affected_tasks)}\n")

    # Print to stdout as well
    if not affected_tasks:
        print("No affected tasks found.")
    else:
        print(
            f"Affected tasks ({len(affected_tasks)}):\n"
            f"{', '.join(affected_tasks)}"
        )
