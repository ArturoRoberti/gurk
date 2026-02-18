import os
import shutil
import subprocess
from contextlib import contextmanager
from functools import cache, wraps
from pathlib import Path
from typing import Any

from filelock import FileLock

from gurk.lib.utils import (
    GIT_MIRRORS_DIR,
    PACKAGE_GIT_CACHE_METADATA_PATH,
    PathLike,
    generate_random_path,
    typecheck,
)

from ..configs import dump_yaml, load_yaml
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


@contextmanager
def _repo_lock(repo: PathLike):
    with FileLock(Path(repo) / ".repo_lock"):
        yield


@typecheck
def _register_mirror(url: str) -> Path:
    """
    Register a new mirror for the specified Git repository URL.
        :NOTE: Distinguishes between the same repo cloned with HTTP and SSH for fetching purposes

    :param url: Git repository URL
    :type url: str
    :return: Path to the created mirror directory
    :rtype: Path
    """
    # Create mirror
    mirror = (
        GIT_MIRRORS_DIR
        / generate_random_path(prefix=Path(url).stem + "_").stem
    )
    mirror.mkdir(parents=True)
    result = _git_run(
        ["git", "clone", "--mirror", "--filter=blob:none", url, str(mirror)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        shutil.rmtree(mirror)
        raise RuntimeError(
            f"Failed to create mirror for {url}:\n{result.stderr}"
        )

    # Update metadata
    with FileLock(GIT_MIRRORS_DIR / ".metadata_lock"):
        meta = load_yaml(PACKAGE_GIT_CACHE_METADATA_PATH) or {}
        meta[url] = str(mirror)
        dump_yaml(meta, PACKAGE_GIT_CACHE_METADATA_PATH)

    return mirror


@cache
@typecheck
def _git_fetch(repo_path: PathLike) -> None:
    """
    Fetch updates for the Git repository at the specified path.

    :param repo_path: Path to the Git repository
    :type repo_path: PathLike
    """
    with _repo_lock(repo_path):
        _git_run(
            ["git", "fetch", "--prune", "--all"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )


@typecheck
def _get_mirror(url: str, fetch: bool = True) -> Path:
    """
    Get the mirror path for the specified Git repository URL, creating it if it doesn't exist.

    :param url: Git repository URL
    :type url: str
    :param fetch: Whether to fetch updates for the mirror after retrieving it
    :type fetch: bool
    :return: Path to the mirror directory
    :rtype: Path
    """
    meta = load_yaml(PACKAGE_GIT_CACHE_METADATA_PATH) or {}
    if url not in meta or not Path(meta[url]).exists():
        mirror = _register_mirror(url)
    else:
        mirror = Path(meta[url])

    if fetch:
        _git_fetch(mirror)

    return mirror
