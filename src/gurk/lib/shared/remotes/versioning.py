import subprocess
from functools import cache
from typing import Literal, overload

from gurk.lib.utils import (
    GURK_METADATA_FILENAME,
    check_version,
    generate_random_path,
    typecheck,
)

from ..configs import load_toml
from .clone import _get_mirror, _git_fetch, _repo_lock, git_clone
from .git_utils import _git_run, is_git_repo
from .types import GitQuery
from .url import edit_url, extract_url


@cache
def _get_commit_timestamp(
    url: str,
    commit: str,
    human_readable: bool,
) -> str | int:
    """
    Get the timestamp of a specific commit in the given Git repository.

    :param url: Git repository URL
    :type url: str
    :param commit: Commit hash to get the timestamp for
    :type commit: str
    :param human_readable: Whether to return the timestamp in human-readable ISO 8601 format
    :type human_readable: bool
    :return: Commit timestamp in ISO 8601 format
    :rtype: str if 'human_readable' else int
    :raises ValueError: If the repository does not exist
    :raises CalledProcessError: If git commands fail for various reasons
    """
    # Check that the repo exists
    if not is_git_repo(url):
        raise ValueError(
            f"Repository {url} does not exist or is not accessible."
        )

    # Fetch updates
    mirror = _get_mirror(url)
    _git_fetch(mirror)

    # Get commit timestamp
    with _repo_lock(mirror):
        format_str = "%cI" if human_readable else "%ct"
        result = _git_run(
            ["git", "show", "--no-patch", f"--format={format_str}", commit],
            cwd=mirror,
            capture_output=True,
            text=True,
            check=True,
        )
        stdout = result.stdout.strip()
        return stdout if human_readable else int(stdout)


@overload
def get_commit_timestamp(
    repo: str | GitQuery,
    commit: str,
    *,
    human_readable: Literal[False] = ...,
) -> int:
    ...


@overload
def get_commit_timestamp(
    repo: str | GitQuery,
    commit: str,
    *,
    human_readable: Literal[True] = ...,
) -> str:
    ...


@typecheck
def get_commit_timestamp(
    repo: str | GitQuery,
    commit: str,
    *,
    human_readable: bool = False,
) -> str | int:
    """
    Get the timestamp of a specific commit in the given Git repository.

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :param commit: Commit hash to get the timestamp for
    :type commit: str
    :param human_readable: Whether to return the timestamp in human-readable ISO 8601 format
    :type human_readable: bool
    :return: Commit timestamp in ISO 8601 format
    :rtype: str if 'human_readable' else int
    :raises ValueError: If the repository does not exist
    :raises CalledProcessError: If git commands fail for various reasons
    """
    return _get_commit_timestamp(
        extract_url(repo),
        commit,
        human_readable,
    )


@typecheck
def commit_exists(
    repo: str | GitQuery,
    commit: str,
) -> bool:
    """
    Check if a specific commit exists in the given Git repository.

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :param commit: Commit hash to check
    :type commit: str
    :return: True if the commit exists, False otherwise
    :rtype: bool
    :raises ValueError: If the repository does not exist
    :raises CalledProcessError: If git commands fail for various reasons
    """
    try:
        get_commit_timestamp(repo, commit)
        return True
    except subprocess.CalledProcessError:
        return False


@cache
@typecheck
def _commit2version(
    url: str,
    commit: str | None,
) -> str | None:
    """
    Return the version string associated with a specific commit in the given Git repository, or None if not found.
        :NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param url: Git repository URL
    :type url: str
    :param commit: Commit hash to find the version for. If None, uses the latest commit on the default branch.
    :type commit: str | None
    :return: Version string associated with the commit, or None if not found
    :rtype: str | None
    :raises ValueError: If the repository does not exist
    :raises CalledProcessError: If git commands fail for various reasons
    """
    # Check that the repo exists
    if not is_git_repo(url):
        raise ValueError(
            f"Repository {url} does not exist or is not accessible."
        )

    # Save the versioning file to a temporary location
    tmp_file = generate_random_path(suffix=".toml")

    try:
        # Clone the versioning file
        git_query = edit_url(url, commit=commit, path=GURK_METADATA_FILENAME)
        git_clone(
            git_query, dest=tmp_file
        )  # TODO: Do without cloning resp. via git show? Then, versioning can include other functions and come above clone.py in hierarchy

        # Load the versioning file
        version = load_toml(tmp_file)["project"]["version"]

        # Parse version
        if not check_version(version):
            raise ValueError
    except Exception:
        version = None
    finally:
        tmp_file.unlink()
        return version


@typecheck
def commit2version(
    repo: str | GitQuery,
    commit: str | None = None,
) -> str | None:
    """
    Return the version string associated with a specific commit in the given Git repository, or None if not found.
        :NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :param commit: Commit hash to find the version for. If None, uses the latest commit on the default branch.
    :type commit: str | None
    :return: Version string associated with the commit, or None if not found
    :rtype: str | None
    """
    return _commit2version(extract_url(repo), commit)


@typecheck
def get_latest_version(
    repo: str | GitQuery,
) -> str | None:
    """
    Return the latest version string from the pyproject.toml file of a git repo, or None if not found.
        :NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :return: Latest version string, or None if not found
    :rtype: str | None
    """
    return commit2version(repo)
