import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from functools import cache, wraps
from pathlib import Path
from typing import Any, Literal, TypeAlias, TypedDict, overload
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
from filelock import FileLock

from gurk.lib.utils.common import (
    PACKAGE_CACHE_PATH,
    PathLike,
    check_version,
    generate_random_path,
)
from gurk.lib.utils.configs import dump_yaml, load_toml, load_yaml
from gurk.lib.utils.typed_dict import fill_typed_dict, validate_typed_dict

GIT_MIRRORS_DIR = PACKAGE_CACHE_PATH / "git_mirrors"
GIT_MIRRORS_DIR.mkdir(parents=True, exist_ok=True)

PACKAGE_GIT_CACHE_METADATA_PATH = GIT_MIRRORS_DIR / "registry.yaml"
PACKAGE_GIT_CACHE_METADATA_PATH.touch(exist_ok=True)


@contextmanager
def _repo_lock(repo: PathLike):
    with FileLock(Path(repo) / ".repo_lock"):
        yield


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


class GitQueryDict(TypedDict):
    """TypedDict representing the parsed components of a GitQuery string"""

    # fmt: off
    url:     str
    branch:  None | str
    commit:  None | str
    version: None | str
    path:    None | str
    # fmt: on


GIT_QUERY_VERSIONING_FIELDS = {"branch", "commit", "version"}

# See '_parse_git_query' function for expected format
GitQuery: TypeAlias = str


def _parse_git_query(repo: GitQuery) -> GitQueryDict:
    """
    Parse a GitQuery string of the form `<repo_url>[?<param>=<value>&...]` into its components

    Examples:
    ```
        "https://github.com/user/repo.git"
        "https://github.com/user/repo.git?branch=main"
        "https://github.com/user/repo.git?path=subdir&commit=abc123&branch=dev"
    ```

    Supported query parameters:
        - branch: branch name
        - commit: commit hash (overrides branch if both provided)
        - version: version string to find the corresponding commit for (overrides branch if both provided)
        - path: subdirectory path within the repo

    :param repo: GitQuery string of the above format
    :type repo: GitQuery
    :return: Parsed GitQueryDict
    :rtype: GitQueryDict
    """
    parts = urlparse(repo)
    query = parse_qs(parts.query)
    return {
        "url": repo.split("?", 1)[0],
        "branch": query.get("branch", [None])[0],
        "commit": query.get("commit", [None])[0],
        "version": query.get("version", [None])[0],
        "path": query.get("path", [None])[0],
    }


def parse_git_query(repo: str | GitQuery | GitQueryDict) -> GitQueryDict:
    """
    Parse a Git repository input which can be either a URL or a GitQuery.

    :param repo: Git repository URL, GitQuery string, or GitQueryDict dictionary
    :type repo: str | GitQuery | GitQueryDict
    :return: Parsed GitQueryDict dictionary
    :rtype: GitQueryDict
    :raises ValueError: For invalid input types
    """
    if isinstance(repo, str):
        parsed = _parse_git_query(repo)
    elif isinstance(repo, dict):
        parsed = fill_typed_dict(repo, GitQueryDict)
        if not validate_typed_dict(parsed, GitQueryDict):
            # There are extra fields
            extra_fields = set(repo.keys()) - set(
                GitQueryDict.__annotations__.keys()
            )
            if extra_fields:
                raise ValueError(
                    f"Invalid fields in GitQueryDict dictionary: {extra_fields}"
                )

            # There are wrong types
            wrong_types = {
                k
                for k, v in repo.items()
                if not isinstance(v, GitQueryDict.__annotations__[k])
            }
            if wrong_types:
                raise ValueError(
                    f"Wrong types for fields in GitQueryDict dictionary: {wrong_types}"
                )

            # Other validation errors
            raise ValueError("Invalid GitQueryDict dictionary provided.")
    else:
        raise ValueError(
            "Invalid repo input. Must be GitQuery string or GitQueryDict dict."
        )

    return parsed


def extract_url(repo: str | GitQuery | GitQueryDict) -> str:
    """
    Extract the URL from a string. If any string other than a GitQuery is given, it is returned as-is.

    :param repo: Git repository URL, GitQuery string, or GitQueryDict dictionary
    :type repo: str | GitQuery | GitQueryDict
    :return: URL without query parameters
    :rtype: str
    """
    return parse_git_query(repo)["url"]


def edit_url(url: str, **kwargs: dict[str, str | None]) -> str:
    """
    Add, update, or remove query parameters in a URL.

    :param url: Original URL
    :type url: str
    :param kwargs: Query parameters to add/update (key=value) or remove (key=None)
    :type kwargs: str | None
    :return: Modified URL with updated query parameters
    :rtype: str
    :raises ValueError: If the input kwargs are invalid
    """
    if not all(
        isinstance(k, str) and (isinstance(v, str) or v is None)
        for k, v in kwargs.items()
    ):
        raise ValueError(
            "All keys in kwargs must be strings and values must be strings or None."
        )

    parts = urlparse(url)
    query = parse_qs(parts.query)

    for key, value in kwargs.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = [value]

    new_query = urlencode(query, doseq=True)
    parts = parts._replace(query=new_query)
    return urlunparse(parts)


@cache
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


def is_git_repo(repo: str | GitQuery) -> bool:
    """
    Check if a string is a valid Git repository URL. Also checks existence of the repo.

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :return: True if the string is a valid Git repository, False otherwise
    :rtype: bool
    """
    return _is_git_repo(extract_url(repo))


@cache
def is_url(url: str) -> bool:
    """
    Check if a string is a valid URL and (optionally) if the URL exists.

    :param url: String to check
    :type url: str
    :return: True if the string is a valid URL, False otherwise
    :rtype: bool
    """
    response = requests.get(url, timeout=30, headers={"Accept-Encoding": "*"})
    return response.status_code == 200


def _register_mirror(url: str) -> Path:
    """
    Register a new mirror for the specified Git repository URL.
        NOTE: Distinguishes between the same repo cloned with HTTP and SSH for fetching purposes

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


def _get_mirror(url: str) -> Path:
    """
    Get the mirror path for the specified Git repository URL, creating it if it doesn't exist.

    :param url: Git repository URL
    :type url: str
    :return: Path to the mirror directory
    :rtype: Path
    """
    meta = load_yaml(PACKAGE_GIT_CACHE_METADATA_PATH) or {}
    if url not in meta or not Path(meta[url]).exists():
        return _register_mirror(url)
    else:
        return Path(meta[url])


@cache
def _version2commit(
    url: str,
    version: str,
) -> str | None:
    """
    Return the commit hash where a specified version change was made
    in the pyproject.toml file of a git repo, or None if not found.

        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml

    :param url: Git repository URL
    :type url: str
    :param version: Version string to search for
    :type version: str
    :return: Commit hash where the version was added, or None if not found
    :rtype: str | None
    :raises ValueError: If the repository does not exist or if the version string is invalid
    :raises CalledProcessError: If git commands fail for various reasons
    """
    # Check that version is valid
    if not check_version(version):
        raise ValueError(f"Invalid version string: '{version}'")

    # Check that the repo exists
    if not is_git_repo(url):
        raise ValueError(
            f"Repository {url} does not exist or is not accessible."
        )

    # Fetch updates
    mirror = _get_mirror(url)
    _git_fetch(mirror)

    with _repo_lock(mirror):
        # Get commits that touched the versioning file, newest first
        version_file = "pyproject.toml"
        result = _git_run(
            ["git", "rev-list", "HEAD", "--", version_file],
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
                ["git", "show", commit, "--", version_file],
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


def version2commit(
    repo: str | GitQuery,
    version: str,
) -> str | None:
    """
    Return the commit hash where a specified version change was made
    in the pyproject.toml file of a git repo, or None if not found.

        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml

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
    # Fetch updates
    mirror = _get_mirror(url)
    _git_fetch(mirror)

    # Get default branch from remote info
    with _repo_lock(mirror):
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


@cache
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

    # Fetch updates
    mirror = _get_mirror(url)
    _git_fetch(mirror)

    # Get commit hash
    with _repo_lock(mirror):
        result = _git_run(
            ["git", "rev-parse", commit],
            cwd=mirror,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


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
    :raises ValueError: If the repository does not exist or if version cannot be resolved to a commit
    :raises CalledProcessError: If git commands fail for various reasons
    """
    parsed = parse_git_query(repo)

    if parsed["commit"]:
        ref = parsed["commit"]
    elif parsed["version"]:
        # Find commit for version
        commit = version2commit(parsed["url"], parsed["version"])
        if not commit:
            raise ValueError(
                f"Version '{parsed['version']}' not found in repository '{parsed['url']}'"
            )
        ref = commit
    elif parsed["branch"]:
        ref = parsed["branch"]
    else:
        # Get default branch
        ref = get_default_branch(parsed["url"])

    if to_commit:
        # Resolve to commit hash
        ref = get_commit(parsed["url"], ref)

    return ref


def git_clone(
    repo: str | GitQuery | GitQueryDict,
    dest: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """
    Clone a Git repository or specific files/directories from it to the specified destination path.

    :param repo: Git repository URL, GitQuery string, or GitQueryDict dictionary representing the repository to clone
    :type repo: str | GitQuery | GitQueryDict
    :param dest: Destination path to clone the files as. Required if cloning specific files/directories.
    :type dest: Path | None
    :param overwrite: Whether to overwrite existing path
    :type overwrite: bool
    :return: Path to the cloned files
    :rtype: Path
    :raises ValueError: For invalid input types, directly or downstream
    :raises CalledProcessError: If git commands fail for various reasons
    """
    # Handle inputs
    ## repo
    parsed = parse_git_query(repo)
    ## dest
    if not isinstance(dest, Path) and dest is not None:
        raise ValueError("Destination 'dest' must be a Path or None.")
    ## overwrite
    if not isinstance(overwrite, bool):
        raise ValueError("Parameter 'overwrite' must be a boolean.")

    if parsed["path"]:
        # Clone specific files/directories
        if dest is None:
            raise ValueError(
                "Destination path must be specified when cloning specific files/directories from a Git repository."
            )
    else:
        # Clone entire repo
        if dest is None:
            dest = Path(Path(parsed["url"]).stem)
        elif dest.suffix:
            raise ValueError(
                "Destination path for cloning entire repository cannot be a file."
            )

    # Check if the repository exists
    if not is_git_repo(parsed["url"]):
        raise ValueError(
            f"Repository '{parsed['url']}' does not exist or is not accessible."
        )

    # Check if destination exists
    if dest.exists() and not overwrite:
        raise ValueError(
            f"Destination path '{dest}' already exists. Use 'overwrite=True' to overwrite."
        )

    # Determine ref to clone (commit > version > branch or default branch)
    ref = determine_ref(repo)

    # Fetch updates
    mirror = _get_mirror(parsed["url"])
    _git_fetch(mirror)

    with _repo_lock(mirror):
        # Pull file(s)
        _git_run(
            ["git", "archive", ref, parsed["path"] or "."],
            cwd=mirror,
            check=True,
            capture_output=True,
        )

        # Clean up existing destination
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()

        # Clone to destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        if parsed["path"]:
            # Clone specific files/directories
            ## Clone to temporary location
            temp_dir = generate_random_path(
                prefix="gurk_git_clone_", create=True
            )
            git_proc = subprocess.Popen(
                ["git", "archive", ref, parsed["path"]],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=mirror,
            )
            subprocess.run(
                ["tar", "-x"],
                stdin=git_proc.stdout,
                check=True,
                capture_output=True,
                cwd=temp_dir,
            )
            git_proc.stdout.close()
            git_proc.wait()

            ## Move to final destination
            src = temp_dir / parsed["path"]
            shutil.move(str(src), str(dest))
            shutil.rmtree(temp_dir)

        else:
            # Clone entire repo
            _git_run(
                ["git", "clone", str(mirror), str(dest)],
                check=True,
                capture_output=True,
            )
            _git_run(
                ["git", "checkout", ref],
                cwd=dest,
                check=True,
                capture_output=True,
            )

    return dest


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
def _commit2version(
    url: str,
    commit: str | None,
) -> str | None:
    """
    Return the version string associated with a specific commit in the given Git repository, or None if not found.
        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

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
        git_query = edit_url(url, commit=commit, path="pyproject.toml")
        git_clone(git_query, dest=tmp_file)

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


def commit2version(
    repo: str | GitQuery,
    commit: str | None = None,
) -> str | None:
    """
    Return the version string associated with a specific commit in the given Git repository, or None if not found.
        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :param commit: Commit hash to find the version for. If None, uses the latest commit on the default branch.
    :type commit: str | None
    :return: Version string associated with the commit, or None if not found
    :rtype: str | None
    """
    return _commit2version(extract_url(repo), commit)


def get_latest_version(
    repo: str | GitQuery,
) -> str | None:
    """
    Return the latest version string from the pyproject.toml file of a git repo, or None if not found.
        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param repo: Git repository URL or GitQuery (in which case only the URL is used)
    :type repo: str | GitQuery
    :return: Latest version string, or None if not found
    :rtype: str | None
    """
    return commit2version(repo)
