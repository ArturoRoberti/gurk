import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import networkx as nx

try:
    from gurk.utils.common import (
        DEFAULT_CONFIG_FILE,
        PACKAGE_SRC_PATH,
        get_script_path,
    )
    from gurk.utils.scripts import (
        ScriptBlockTypes,
        get_block_spans,
        iter_configs,
        iter_scripts,
    )
    from gurk.utils.tasks import RUNNER_SPECIFIC_TASKS
    from gurk.utils.yaml import load_yaml
except ImportError:
    raise ImportError(
        "The gurk package needs to be installed to run this script."
    )


def _parse_diff_changed_lines(diff_text: str) -> Dict[str, Set[int]]:
    """
    Parse a unified diff text and return a mapping of file paths to changed line numbers.
        NOTE: This currently also counts changed comments and blank lines.

    :param diff_text: The unified diff text
    :type diff_text: str
    :return: Mapping of file paths to sets of changed line numbers
    :rtype: Dict[str, Set[int]]
    """
    changed: Dict[str, Set[int]] = {}
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

    # Prepend package path to file paths
    return {
        str(PACKAGE_SRC_PATH.parents[1] / k): v for k, v in changed.items()
    }


def _affected_blocks(path: Path, changed_lines: Set[int]) -> Set[str]:
    """
    Determine which top-level blocks (functions/entrypoint) are affected by the changed lines.
        NOTE: Assumes scripts are valid, i.e. only contain functions and an entrypoint (and imports for Python)

    :param path: Path to the script file
    :type path: Path
    :param changed_lines: Set of changed line numbers in the script
    :type changed_lines: Set[int]
    :return: Set of affected block names (function names or None for entrypoint)
    :rtype: Set[str]
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


def compute_affected_tasks(diff_text: str) -> List[str]:
    """
    Compute the set of affected tasks based on the given diff text.

    :param diff_text: The unified diff text
    :type diff_text: str
    :return: Set of affected task names
    :rtype: Set[str]
    """
    # Parse diff to get changed line numbers per file
    changed_lines_map = _parse_diff_changed_lines(diff_text)

    # Find affected script blocks (functions/entrypoints)
    affected_script_blocks: Dict[Path, Set[str]] = {}
    for file_path in iter_scripts():
        affected_script_blocks[file_path] = _affected_blocks(
            file_path, changed_lines_map.get(str(file_path), set())
        )

    # Find affected config files
    affected_config_files = set()
    for file_path in iter_configs():
        if str(file_path) in changed_lines_map:
            affected_config_files.add(file_path.name)

    # Determine affected tasks
    default_config = load_yaml(DEFAULT_CONFIG_FILE)
    tasks = {k: v for k, v in default_config.items() if not k.startswith("_")}
    affected_tasks: Set[str] = set()
    for task_name, task in tasks.items():
        # Affected script block
        command = task_name.split("-", 1)[0]
        script = get_script_path(task["script"], command)
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


def main():
    # Compute affected tasks from git diff read from stdin
    affected_tasks = compute_affected_tasks(sys.stdin.read())

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


if __name__ == "__main__":
    main()
