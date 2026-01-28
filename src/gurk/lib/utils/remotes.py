import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, TypeAlias, TypedDict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
import tomllib
from filelock import FileLock
from ruamel.yaml import YAML

from gurk.lib.utils.common import (
    PACKAGE_CACHE_PATH,
    check_version,
    generate_random_path,
)
from gurk.lib.utils.configs import load_toml, load_yaml
from gurk.lib.utils.typed_dict import fill_typed_dict, validate_typed_dict

PACKAGE_GIT_CACHE_PATH = PACKAGE_CACHE_PATH / "git"
MIRRORS_DIR = PACKAGE_GIT_CACHE_PATH / "mirrors"
MIRRORS_DIR.mkdir(parents=True, exist_ok=True)

PACKAGE_GIT_CACHE_METADATA_PATH = PACKAGE_GIT_CACHE_PATH / "registry.yaml"
PACKAGE_GIT_CACHE_METADATA_PATH.touch(exist_ok=True)


@contextmanager
def _repo_lock(repo: Path):
    with FileLock(repo / ".repo_lock"):
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


class GitRefInfo(TypedDict):
    """TypedDict representing parsed Git reference information."""

    # fmt: off
    url:     str
    branch:  str | None
    commit:  str | None
    path:    str | None
    version: str | None
    # fmt: on


GitRef: TypeAlias = str  # See 'parse_git_ref' function for expected format


def parse_git_ref(repo: GitRef) -> GitRefInfo:
    """
    Parse a Git repo reference string of the form `<repo_url>[?<param>=<value>&...]`

    Examples:
    ```
        "https://github.com/user/repo.git"
        "https://github.com/user/repo.git?branch=main"
        "https://github.com/user/repo.git?path=subdir&commit=abc123&branch=dev"
    ```

    Supported query parameters:
        - branch: branch name
        - commit: commit hash (overrides branch if both provided)
        - path: subdirectory path within the repo

    :param repo: GitRef string of the above format
    :type repo: GitRef
    :return: Parsed GitRefInfo dictionary with keys: 'url', 'branch', 'commit', 'path'.
             Missing fields are set to None.
    :rtype: GitRefInfo
    """
    parts = urlparse(repo)
    query = parse_qs(parts.query)
    return {
        "url": repo.split("?", 1)[0],
        "branch": query.get("branch", [None])[0],
        "commit": query.get("commit", [None])[0],
        "path": query.get("path", [None])[0],
        "version": query.get("version", [None])[0],
    }


def extract_url(repo: str | GitRef) -> str:
    """
    Extract the URL from a string. If any string other than a GitRef is given, it is returned as-is.

    :param repo: str string
    :type repo: str | GitRef
    :return: URL without query parameters
    :rtype: str
    """
    return parse_git_ref(repo)["url"]


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


def is_git_repo(repo: str | GitRef) -> bool:
    """
    Check if a string is a valid Git repository URL. Also checks existence of the repo.

    :param repo: Git repository URL or GitRef (in which case only the URL is used)
    :type repo: str | GitRef
    :return: True if the URL is a valid Git repository, False otherwise
    :rtype: bool
    """
    result = _git_run(
        ["git", "ls-remote", extract_url(repo)],
        timeout=10,
        capture_output=True,
    )
    return result.returncode == 0


def is_url(string: str, check: bool = True) -> bool:
    """
    Check if a string is a valid URL and (optionally) if the URL exists.

    :param string: String to check
    :type string: str
    :param check: Whether to check if the URL exists (default: True)
    :type check: bool
    :return: True if the string is a valid URL, False otherwise
    :rtype: bool
    """
    parsed = urlparse(string)
    if not all([parsed.scheme, parsed.netloc]):
        return False

    if check:
        response = requests.get(
            string, timeout=60, headers={"Accept-Encoding": "*"}
        )
        if not response.status_code == 200:
            return False

    return True


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
        MIRRORS_DIR / generate_random_path(prefix=Path(url).stem + "_").stem
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
    metadata_lock = PACKAGE_GIT_CACHE_PATH / ".metadata_lock"
    with FileLock(metadata_lock):
        meta = load_yaml(PACKAGE_GIT_CACHE_METADATA_PATH) or {}
        meta[url] = str(mirror)
        with PACKAGE_GIT_CACHE_METADATA_PATH.open("w") as f:
            YAML().dump(meta, f)

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


def version2commit(
    repo: str | GitRef,
    version: str,
) -> str | None:
    """
    Return the commit hash where a specified version change was made
    in the pyproject.toml file of a git repo, or None if not found.
        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml

    :param repo: Git repository URL or GitRef (in which case only the URL is used)
    :type repo: str | GitRef
    :param version: Version string to search for
    :type version: str
    :return: Commit hash where the version was added, or None if not found
    :rtype: str | None
    :raises ValueError: If the repository does not exist
    :raises CalledProcessError: If git commands fail for various reasons
    """
    # Check that the repo exists
    if not is_git_repo(repo):
        raise ValueError(
            f"Repository {repo} does not exist or is not accessible."
        )

    mirror = _get_mirror(extract_url(repo))
    with _repo_lock(mirror):
        # Fetch updates
        _git_run(
            ["git", "fetch", "--prune", "--all"],
            cwd=mirror,
            check=True,
            capture_output=True,
        )

        # Get commits that touched the versioning file, newest first
        version_file = "pyproject.toml"
        result = _git_run(
            ["git", "rev-list", "HEAD", "--", version_file],
            cwd=mirror,
            capture_output=True,
            text=True,
            check=True,
        )
        revs = result.stdout.splitlines()

        # Search for version addition in diffs
        version_re = re.compile(
            rf'^\+version\s*=\s*"{re.escape(version)}"\s*$'
        )
        for commit in revs:
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


def git_clone(
    repo: GitRef | GitRefInfo,
    dest: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """
    Clone a Git repository or specific files/directories from it to the specified destination path.

    :param repo: GitRef string or GitRefInfo dictionary representing the repository to clone
    :type repo: GitRef | GitRefInfo
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
    if isinstance(repo, GitRef):
        parsed = parse_git_ref(repo)
    elif isinstance(repo, dict):
        parsed = fill_typed_dict(repo, GitRefInfo)
        if not validate_typed_dict(parsed, GitRefInfo):
            extra_fields = set(repo.keys()) - set(
                GitRefInfo.__annotations__.keys()
            )
            if extra_fields:
                raise ValueError(
                    f"Invalid fields in GitRefInfo dictionary: {extra_fields}"
                )

            wrong_types = {
                k
                for k, v in repo.items()
                if not isinstance(v, GitRefInfo.__annotations__[k])
            }
            if wrong_types:
                raise ValueError(
                    f"Wrong types for fields in GitRefInfo dictionary: {wrong_types}"
                )

            raise ValueError("Invalid GitRefInfo dictionary provided.")
    else:
        raise ValueError(
            "Invalid repo input. Must be GitRef string or GitRefInfo dict."
        )
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
    if parsed["commit"]:
        ref = parsed["commit"]
    elif parsed["version"]:
        # Find commit for version
        ref = version2commit(parsed["url"], parsed["version"])
        if not ref:
            raise ValueError(
                f"Version '{parsed['version']}' not found in repository '{parsed['url']}'."
            )
    elif parsed["branch"]:
        ref = parsed["branch"]
    else:
        # Get default branch
        ref = (
            _git_run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=_get_mirror(parsed["url"]),
                capture_output=True,
                text=True,
                check=True,
            )
            .stdout.strip()
            .removeprefix("refs/remotes/origin/")
        )

    # Update mirror with requested ref
    mirror = _get_mirror(parsed["url"])
    with _repo_lock(mirror):
        # Fetch updates
        _git_run(
            ["git", "fetch", "--prune", "--all"],
            cwd=mirror,
            check=True,
            capture_output=True,
        )
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
            before = set(dest.parent.iterdir())
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
                cwd=dest.parent,
            )
            git_proc.stdout.close()
            git_proc.wait()

            # Rename as specified by dest
            after = set(dest.parent.iterdir())
            created = after - before
            if len(created) != 1:
                raise subprocess.CalledProcessError(
                    f"Unexpected: {len(created)} items cloned when expecting just one for "
                    f"path '{parsed['path']}' in repository '{parsed['url']}' at ref '{ref}'."
                )
            else:
                created_path = created.pop()
                created_path.rename(dest)

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


# TODO: Use in periodic workflow
def get_latest_version(
    repo: str | GitRef,
) -> str | None:
    """
    Return the latest version string from the pyproject.toml file of a git repo, or None if not found.
        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param repo: Git repository URL or GitRef (in which case only the URL is used)
    :type repo: str | GitRef
    :return: Latest version string, or None if not found
    :rtype: str | None
    """
    # Save the versioning file to a temporary location
    tmp_file = generate_random_path(suffix=".toml")

    try:
        # Clone the versioning file
        git_clone(extract_url(repo) + "?path=pyproject.toml", dest=tmp_file)

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


# TODO: Keep?
def commit2version(
    repo: str | GitRef,
    commit: str,
) -> str | None:
    """
    Return the version string at a specified commit in the pyproject.toml file of a git repo, or None if not found.
        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml

    :param repo: Git repository URL or GitRef (in which case only the URL is used)
    :type repo: str | GitRef
    :param commit: Commit hash to search for
    :type commit: str
    :return: Version string at the specified commit, or None if not found
    :rtype: str | None
    :raises ValueError: If the repository does not exist
    :raises CalledProcessError: If git commands fail for various reasons
    """
    # Check that the repo exists
    if not is_git_repo(repo):
        raise ValueError(
            f"Repository {repo} does not exist or is not accessible."
        )

    mirror = _get_mirror(extract_url(repo))
    with _repo_lock(mirror):
        # Fetch updates
        _git_run(
            ["git", "fetch", "--prune", "--all"],
            cwd=mirror,
            check=True,
            capture_output=True,
        )

        # Get pyproject.toml at the specified commit
        result = _git_run(
            ["git", "show", f"{commit}:pyproject.toml"],
            cwd=mirror,
            capture_output=True,
            text=True,
            check=True,
            errors="ignore",
        )
        toml_content = result.stdout

        # Parse version from toml content
        try:
            toml_data = tomllib.loads(toml_content)
            version = toml_data["project"]["version"]
            if not check_version(version):
                raise ValueError
            return version
        except Exception:
            return None
