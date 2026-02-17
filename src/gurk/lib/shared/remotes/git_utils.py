import os
import subprocess
from functools import cache, wraps
from typing import Any

from gurk.lib.utils import typecheck

from .types import GitQuery
from .url import extract_url


@wraps(subprocess.run)
def _git_run(
    *args: Any,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    Wrapper around subprocess.run to run a git command with SSH options to disable strict host key checking.

    :return: CompletedProcess result of the command
    :rtype: CompletedProcess
    """
    # Add GIT_SSH_COMMAND to disable strict host key checking
    if not (kwargs.get("env") and isinstance(kwargs["env"], dict)):
        kwargs["env"] = os.environ.copy()
    kwargs["env"]["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"

    return subprocess.run(*args, **kwargs)


def is_git_installed() -> bool:
    """
    Check if Git is installed on the system.

    :return: True if Git is installed, False otherwise
    :rtype: bool
    """
    try:
        _git_run(["git", "--version"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        return False
    else:
        return True


@cache
@typecheck
def _is_git_repo(url: str) -> bool:
    """
    Check if the repository at the given URL exists.

    :param url: Git repository URL
    :type url: str
    :return: True if the string is a valid Git repository, False otherwise
    :rtype: bool
    """
    result = _git_run(
        ["git", "ls-remote", extract_url(url)],
        timeout=30,
        capture_output=True,
    )
    return result.returncode == 0


@typecheck
def is_git_repo(repo: str | GitQuery) -> bool:
    """
    Check if a string is a valid Git repository URL. Also checks existence of the repo.

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :return: True if the string is a valid Git repository, False otherwise
    :rtype: bool
    """
    return _is_git_repo(extract_url(repo))
