import os
import shlex
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, TypedDict
from urllib.parse import parse_qs, urlparse

import git


def run_git_command(
    command: str, timeout: int = 300
) -> subprocess.CompletedProcess:
    """
    Run a git command with SSH options to disable strict host key checking.

    :param command: Git command to run
    :type command: str
    :param timeout: Timeout in seconds
    :type timeout: int
    :return: CompletedProcess result of the command
    :rtype: CompletedProcess
    """
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"
    return subprocess.run(
        shlex.split(command),
        env=env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


class GitRefInfo(TypedDict):
    """TypedDict representing parsed Git reference information."""

    # fmt: off
    url:    str
    branch: Optional[str]
    commit: Optional[str]
    path:   Optional[str]
    depth:  Optional[int]
    # fmt: on


GitRef = str  # See 'parse_git_ref' function for expected format


def parse_git_ref(repo: GitRef) -> GitRefInfo:
    """
    Parse a Git repo reference string of the form `<repo_url>[?<param>=<value>&...]`

    Examples:
    ```
        "https://github.com/user/repo.git"
        "https://github.com/user/repo.git?branch=main"
        "https://github.com/user/repo.git?commit=abc123&branch=dev&depth=1"
    ```

    Supported query parameters:
        - branch: branch name
        - commit: commit hash (overrides branch if both provided)
        - path: subdirectory path within the repo
        - depth: clone depth (integer)

    :param repo: GitRef string of the above format
    :type repo: GitRef
    :return: Parsed GitRefInfo dictionary with keys: 'url', 'branch', 'commit', 'path', 'depth'.
             Missing fields are set to None. Depth is returned as an int if present.
    :rtype: GitRefInfo
    """
    parts = urlparse(repo)
    query = parse_qs(parts.query)

    # Get elements
    url = repo.split("?", 1)[0]
    branch = query.get("branch", [None])[0]
    commit = query.get("commit", [None])[0]
    path = query.get("path", [None])[0]
    depth_val = query.get("depth", [None])[0]
    try:
        depth_val = int(depth_val)
    except Exception:
        depth_val = None

    return {
        "url": url,
        "branch": branch,
        "commit": commit,
        "path": path,
        "depth": depth_val,
    }


def gitref_dict2str(git_ref_info: GitRefInfo) -> GitRef:
    """
    Convert a GitRefInfo dict back to a GitRef string.

    :param git_ref_info: GitRefInfo dictionary
    :type git_ref_info: GitRefInfo
    :return: GitRef string
    :rtype: GitRef
    """
    url = git_ref_info["url"]
    query_params = []
    if git_ref_info.get("branch"):
        query_params.append(f"branch={git_ref_info['branch']}")
    if git_ref_info.get("commit"):
        query_params.append(f"commit={git_ref_info['commit']}")
    if git_ref_info.get("path"):
        query_params.append(f"path={git_ref_info['path']}")
    if git_ref_info.get("depth") is not None:
        query_params.append(f"depth={git_ref_info['depth']}")

    if query_params:
        return f"{url}?{'&'.join(query_params)}"
    else:
        return url


def is_git_repo(repo: GitRef) -> bool:
    """
    Check if a string is a valid Git repository URL.

    :param repo: GitRef string to check
    :type repo: GitRef
    :return: True if the URL is a valid Git repository, False otherwise
    :rtype: bool
    """
    parsed = parse_git_ref(repo)
    result = run_git_command(f"git ls-remote {parsed['url']}", timeout=10)
    return result.returncode == 0


def handle_existing_dest(dest_path: Path, overwrite: bool) -> bool:
    """
    Handle existing destination path before cloning.

    :param dest_path: Path to the destination
    :type dest_path: Path
    :param overwrite: Whether to overwrite existing path
    :type overwrite: bool
    :return: True if destination is ready for cloning, False otherwise
    :rtype: bool
    """
    if dest_path.exists():
        if not overwrite:
            print(f"Destination '{dest_path}' already exists.")
            return False
        else:
            if dest_path.is_dir():
                shutil.rmtree(dest_path)
            else:
                dest_path.unlink()
    return True


def clone_git_repo(
    repo: GitRef, dest_path: Optional[Path] = None, overwrite: bool = False
) -> Optional[Path]:
    """
    Clone a Git repository to the specified destination path.

    :param repo: GitRef string of the repository to clone
    :type repo: GitRef
    :param dest_path: Destination path to clone the repository into
    :type dest_path: Optional[Path]
    :param overwrite: Whether to overwrite existing path
    :type overwrite: bool
    :return: Path to the cloned repository or None if cloning failed
    :rtype: Path | None
    """
    parsed = parse_git_ref(repo)

    dest_path = (
        Path(dest_path) if dest_path else Path(Path(parsed["url"]).stem)
    )
    if dest_path.suffix:
        # Error: Cannot clone repo as file
        return None

    if not handle_existing_dest(dest_path, overwrite):
        return None

    try:
        git_clone_cmd = f"git clone {parsed['url']} {dest_path}"
        if parsed["branch"]:
            git_clone_cmd += f" --branch {parsed['branch']}"
        if parsed["depth"] is not None:
            git_clone_cmd += f" --depth {parsed['depth']}"
        result = run_git_command(git_clone_cmd)
        if result.returncode != 0:
            print(f"Git clone failed for {parsed['url']}")
            return None
        repo_obj = git.Repo(dest_path)

        if parsed["commit"]:
            repo_obj.git.fetch("origin", parsed["commit"])
            repo_obj.git.checkout(parsed["commit"])

        return dest_path
    except git.exc.GitCommandError:
        return None


def clone_git_files(
    repo: GitRef, dest_path: Optional[Path] = None, overwrite: bool = False
) -> Optional[Path]:
    """
    Clone specific files or directories from a Git repository.

    :param repo: GitRef string of the repository to clone files from
    :type repo: GitRef
    :param dest_path: Destination path to clone the files into
    :type dest_path: Optional[Path]
    :param overwrite: Whether to overwrite existing path
    :type overwrite: bool
    :return: Path to the cloned files or None if cloning failed
    :rtype: Path | None
    """
    parsed = parse_git_ref(repo)
    if not handle_existing_dest(dest_path, overwrite):
        return None

    if not parsed.get("path"):
        return clone_git_repo(repo, dest_path, overwrite)

    dest_path = (
        Path(dest_path) if dest_path else Path(Path(parsed["url"]).stem)
    )
    if dest_path.suffix and not Path(parsed["path"]).suffix:
        # Error: Cannot clone dir as file
        return None

    with TemporaryDirectory() as tmp_dir:
        repo_path = clone_git_repo(
            repo,
            dest_path=Path(tmp_dir),
            overwrite=True,
        )
        if repo_path is None:
            return None

        src_path = repo_path / parsed["path"]
        if not src_path.exists():
            shutil.rmtree(tmp_dir)
            raise FileNotFoundError(
                f"Path {parsed['path']} not found in repo."
            )

        if src_path.is_dir():
            shutil.copytree(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)

    return dest_path
