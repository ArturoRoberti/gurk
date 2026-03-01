import shutil
import subprocess
from pathlib import Path

from gurk.lib.utils import generate_random_path, typecheck

from .mirror import GitRepositoryMirror
from .types import GitQuery, GitQueryDict
from .url import parse_git_query
from .utils import _git_run, is_git_repo
from .versioning import determine_ref


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
    if not ref:
        raise ValueError(f"Could not determine the given ref from '{repo}'")

    with GitRepositoryMirror(parsed["url"]) as mirror:
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
