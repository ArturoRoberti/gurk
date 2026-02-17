# flake8: noqa: F401
from .clone import (
    determine_ref,
    get_commit,
    get_default_branch,
    git_clone,
    version2commit,
)
from .git_utils import is_git_installed, is_git_repo
from .types import GitQuery, GitQueryDict
from .url import edit_url, extract_url, parse_git_query
from .versioning import (
    commit2version,
    commit_exists,
    get_commit_timestamp,
    get_latest_version,
)
