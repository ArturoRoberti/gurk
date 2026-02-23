import shutil
from contextlib import contextmanager
from functools import cache
from pathlib import Path

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
from .utils import _git_run


class GitRepositoryMirror:
    """
    Context manager for handling Git repository mirrors with automatic fetching and locking.

    :param url: The normalized Git repository URL
    :type url: str
    :param fetch: Whether to automatically fetch updates when entering the context
    :type fetch: bool
    """

    def __init__(self, repo: str | GitQuery, fetch: bool = True):
        self.url = extract_url(repo)
        self.fetch = fetch

    def __enter__(self):
        mirror = self.get_mirror(self.url)
        if self.fetch:
            self.git_fetch(mirror)

        with self.repo_lock(mirror):
            return mirror

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    @staticmethod
    @contextmanager
    @typecheck
    def repo_lock(repo: PathLike):
        with FileLock(Path(repo) / ".repo_lock"):
            yield

    @staticmethod
    @typecheck
    def register_mirror(url: str) -> Path:
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
            [
                "git",
                "clone",
                "--mirror",
                "--filter=blob:none",
                url,
                str(mirror),
            ],
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
    def get_mirror(self, url: str) -> Path:
        """
        Get the mirror path for the specified Git repository URL, creating it if it doesn't exist.

        :param url: Git repository URL
        :type url: str
        :return: Path to the mirror directory
        :rtype: Path
        """
        meta = load_yaml(PACKAGE_GIT_CACHE_METADATA_PATH) or {}
        if url not in meta or not Path(meta[url]).exists():
            mirror = self.register_mirror(url)
        else:
            mirror = Path(meta[url])

        return mirror

    @cache
    @typecheck
    def git_fetch(self, repo_path: PathLike) -> None:
        """
        Fetch updates for the Git repository at the specified path.

        :param repo_path: Path to the Git repository
        :type repo_path: PathLike
        """
        with self.repo_lock(repo_path):
            _git_run(
                ["git", "fetch", "--prune", "--all"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
