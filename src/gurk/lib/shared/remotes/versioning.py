import re
import subprocess
from functools import cache
from typing import Literal, overload

from gurk.lib.utils import GURK_METADATA_FILENAME, check_version, typecheck

from ..configs import load_toml
from .mirror import GitRepositoryMirror
from .types import GitQuery, GitQueryDict
from .url import edit_url, extract_url, parse_git_query
from .utils import _git_run, is_git_repo


@cache
@typecheck
def _version2commit(
    url: str,
    version: str,
) -> str | None:
    """
    Return the commit hash where a specified version change was made in the pyproject.toml file of a git repo, or None if not found.
        :NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml

    :param url: Git repository URL
    :type url: str
    :param version: Version string to search for
    :type version: str
    :return: Commit hash where the version was added, or None if not found
    :rtype: str | None
    :raises ValueError: If the repository does not exist or if the version string is invalid
    :raises CalledProcessError: If git commands fail for various reasons
    """
    # Check that the repo exists
    if not is_git_repo(url):
        raise ValueError(
            f"Repository {url} does not exist or is not accessible."
        )

    # Check that version is valid
    if not check_version(version):
        return None

    with GitRepositoryMirror(url) as mirror:
        # Get commits that touched the versioning file, newest first
        result = _git_run(
            ["git", "rev-list", "HEAD", "--", GURK_METADATA_FILENAME],
            cwd=mirror,
            capture_output=True,
            text=True,
            check=True,
        )
        revisions = result.stdout.splitlines()

        # Search for version addition in diffs
        version_re = re.compile(
            rf'^\+version\s*=\s*"{re.escape(version)}"\s*$'
        )
        for commit in revisions:
            result = _git_run(
                ["git", "show", commit, "--", GURK_METADATA_FILENAME],
                cwd=mirror,
                capture_output=True,
                text=True,
                check=True,
                errors="ignore",
            )
            diff = result.stdout.splitlines()

            for line in diff:
                if version_re.match(line):
                    return commit

    return None


@typecheck
def version2commit(
    repo: str | GitQuery,
    version: str,
) -> str | None:
    """
    Return the commit hash where a specified version change was made in the pyproject.toml file of a git repo, or None if not found.
        :NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :param version: Version string to search for
    :type version: str
    :return: Commit hash where the version was added, or None if not found
    :rtype: str | None
    :raises ValueError: If the repository does not exist or if the version string is invalid
    :raises CalledProcessError: If git commands fail for various reasons
    """
    return _version2commit(extract_url(repo), version)


@cache
@typecheck
def get_default_branch(
    url: str,
) -> str:
    """
    Determine the default branch of a Git repository.

    :param url: Git repository URL
    :type url: str
    :return: Name of the default branch
    :rtype: str
    :raises ValueError: If the repository does not exist or is not a valid Git repository
    :raises CalledProcessError: If git commands fail for various reasons
    :raises RuntimeError: If the default branch cannot be determined
    """
    with GitRepositoryMirror(url) as mirror:
        # Get default branch from remote info
        result = _git_run(
            ["git", "remote", "show", "origin"],
            cwd=mirror,
            capture_output=True,
            text=True,
            check=True,
        )

    # Parse default branch
    origin = result.stdout.splitlines()
    head_line = next(
        (line for line in origin if line.strip().startswith("HEAD branch:")),
        None,
    )
    if head_line is None:
        raise RuntimeError("Could not determine remote HEAD branch")

    # Return default branch
    return head_line.split(":", 1)[1].strip()


@cache
@typecheck
def _get_commit(url: str | GitQuery, commit: str | None) -> str:
    """
    Get the current commit hash of a local Git repository. If a specific commit is provided, checks if it exists and returns its full hash if so.

    :param url: Git repository URL
    :type url: str | GitQuery
    :param commit: Optional commit hash to check and expand. If None, returns the current HEAD commit.
    :type commit: str | None
    :return: Current commit hash
    :rtype: str
    :raises ValueError: If the path is not a valid Git repository
    :raises CalledProcessError: If git commands fail for various reasons
    """
    # Check that the repo exists
    if not is_git_repo(url):
        raise ValueError(
            f"Repository {url} does not exist or is not accessible."
        )

    if commit is None:
        commit = "HEAD"

    with GitRepositoryMirror(url) as mirror:
        # Get commit hash
        result = _git_run(
            ["git", "rev-parse", commit],
            cwd=mirror,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


@typecheck
def get_commit(repo: str | GitQuery, commit: str | None = None) -> str | None:
    """
    Get the current commit hash of a local Git repository. If a specific commit is provided, checks if it exists and returns its full hash if so.

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :param commit: Optional commit hash to check and expand. If None, returns the current HEAD commit.
    :type commit: str | None
    :return: Current commit hash or None if the commit does not exist
    :rtype: str | None
    :raises ValueError: If the path is not a valid Git repository
    """
    try:
        return _get_commit(extract_url(repo), commit)
    except subprocess.CalledProcessError:
        return None


@typecheck
def determine_ref(
    repo: str | GitQuery | GitQueryDict, *, to_commit: bool = False
) -> str:
    """
    Determine the appropriate git ref (branch, version, or commit) to use for the given repository.

    :param repo: Git repository URL, GitQuery string, or GitQueryDict dictionary
    :type repo: str | GitQuery | GitQueryDict
    :param to_commit: Whether to resolve to a commit hash. If False, returns branch or version if available.
    :type to_commit: bool
    :return: Git ref to use (branch name, version string, or commit hash)
    :rtype: str
    :raises ValueError: If the repository does not exist
    :raises CalledProcessError: If git commands fail for various reasons
    """
    parsed = parse_git_query(repo)

    if parsed["commit"]:
        ref = parsed["commit"]
    elif parsed["version"]:
        # Find commit for version
        ref = version2commit(parsed["url"], parsed["version"])
    elif parsed["branch"]:
        ref = parsed["branch"]
    else:
        # Get default branch
        ref = get_default_branch(parsed["url"])

    if to_commit:
        # Resolve to commit hash
        ref = get_commit(parsed["url"], ref)

    return ref


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

    with GitRepositoryMirror(url) as mirror:
        # Get commit timestamp
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

    # Get the full commit
    ref = determine_ref(edit_url(url, commit=commit), to_commit=True)

    with GitRepositoryMirror(url) as mirror:
        # Get the versioning file
        versioning_file = _git_run(
            ["git", "show", f"{ref}:{GURK_METADATA_FILENAME}"],
            cwd=mirror,
            check=True,
            capture_output=True,
            text=True,
        )

    # Load the version
    version = load_toml(versioning_file.stdout, from_str=True)["project"][
        "version"
    ]

    # Parse version
    if check_version(version):
        return version
    else:
        return None


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
