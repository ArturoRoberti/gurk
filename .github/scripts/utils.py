import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
PLUGIN_FOLDER_PREFIX = "src/gurk/plugins/"
DEFAULT_BRANCH = "main"


def get_changed_plugin_folder_names() -> set[str]:
    """
    Get the set of changed plugin folder names under PLUGIN_FOLDER_PREFIX.

    :return: Set of changed plugin folder names
    :rtype: set[str]
    """
    # Get list of changed files under PLUGIN_FOLDER_PREFIX
    diff_output = subprocess.check_output(
        [
            "git",
            "diff",
            "--name-only",
            f"{DEFAULT_BRANCH}..HEAD",
            "--",
            PLUGIN_FOLDER_PREFIX,
        ],
        text=True,
    ).strip()
    if not diff_output:
        return set()

    # Extract unique plugin folder names
    plugins = set()
    for path in diff_output.splitlines():
        if not path.startswith(PLUGIN_FOLDER_PREFIX):
            continue

        remainder = path[len(PLUGIN_FOLDER_PREFIX) :]
        parts = remainder.split("/", 1)

        if len(parts) > 1 and parts[0] not in ("gurk", "template"):
            print(parts)
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
        REPO_ROOT / PLUGIN_FOLDER_PREFIX / p
        for p in get_changed_plugin_folder_names()
    }


def get_changed_plugin_names() -> set[str]:
    """
    Get the set of changed plugin names under PLUGIN_FOLDER_PREFIX.

    :return: Set of changed plugin names
    :rtype: set[str]
    """
    from ruamel.yaml import YAML

    # Load registry.yaml
    registry_path = REPO_ROOT / PLUGIN_FOLDER_PREFIX / "registry.yaml"
    with registry_path.open("r", encoding="utf-8") as f:
        registry_data: dict[str, dict[str, str]] = YAML().load(f)

    # Get list of changed plugin folder names
    changed_plugin_names = get_changed_plugin_folder_names()

    # Map folder names to plugin names using registry
    return {
        k
        for k, v in registry_data.items()
        if v.get("local") in changed_plugin_names
    }
