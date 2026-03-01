# flake8: noqa: F401
from .clone import git_clone
from .types import GitQuery, GitQueryDict
from .url import edit_url, extract_url, is_url, parse_git_query
from .utils import is_git_installed, is_git_repo
from .versioning import (
    commit2version,
    commit_exists,
    determine_ref,
    get_commit,
    get_commit_timestamp,
    get_default_branch,
    get_latest_version,
    version2commit,
)
