from typing import TypeAlias, TypedDict

# See '_parse_git_query' function for expected format
GitQuery: TypeAlias = str


class GitQueryDict(TypedDict):
    """TypedDict representing the parsed components of a GitQuery string"""

    # fmt: off
    url:     str
    branch:  None | str
    commit:  None | str
    version: None | str
    path:    None | str
    # fmt: on
