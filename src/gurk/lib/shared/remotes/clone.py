import re
import shutil
import subprocess
from contextlib import contextmanager
from functools import cache
from pathlib import Path

from filelock import FileLock

from gurk.lib.utils import (
    GIT_MIRRORS_DIR,
    GURK_METADATA_FILENAME,
    PACKAGE_GIT_CACHE_METADATA_PATH,
    PathLike,
    check_version,
    generate_random_path,
    typecheck,
)

from ..configs import dump_yaml, load_yaml
from .git_utils import _git_run, is_git_repo
from .types import GitQuery, GitQueryDict
from .url import extract_url, parse_git_query


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


@typecheck
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


@typecheck
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
