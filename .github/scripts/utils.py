import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
PLUGIN_FOLDER_PREFIX = "src/gurk/plugins/"
DEFAULT_BRANCH = "main"


def get_git_diff(
    path: str | Path | None = None,
    name_only: bool = False,
    staged: bool = True,
) -> str:
    """
    Get the git diff between the default branch and the current HEAD.

    :param path: Optional path to get the diff for/under.
    :type path: str | Path | None
    :param name_only: Whether to return only the names of changed files
    :type name_only: bool
    :param staged: Whether to include staged changes
    :type staged: bool
    :return: The git diff as a string
    :rtype: str
    """
    diff_cmd = [
        "git",
        "diff",
        "--unified=0",
        "--ignore-space-change",
        DEFAULT_BRANCH,
    ]
    if path:
        diff_cmd.extend(["--", str(path)])
    if name_only:
        diff_cmd.insert(2, "--name-only")
    if staged:
        diff_cmd.insert(2, "--staged")

    return subprocess.check_output(diff_cmd, text=True)
