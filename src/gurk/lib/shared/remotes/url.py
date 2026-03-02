# Copyright 2026 Arturo Roberti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import cache
from typing import get_type_hints
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse

import requests

from gurk.lib.utils import full_isinstance, typecheck

from ..dicts import fill_typed_dict
from .types import GitQuery, GitQueryDict


@typecheck
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


@typecheck
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
        if not full_isinstance(parsed, GitQueryDict):
            # There are extra fields
            extra_fields = set(repo.keys()) - set(
                get_type_hints(GitQueryDict).keys()
            )
            if extra_fields:
                raise ValueError(
                    f"Invalid fields in GitQueryDict dictionary: {extra_fields}"
                )

            # There are wrong types
            wrong_types = {
                k
                for k, v in repo.items()
                if not isinstance(v, get_type_hints(GitQueryDict)[k])
            }
            if wrong_types:
                raise ValueError(
                    f"Wrong types for fields in GitQueryDict dictionary: {wrong_types}"
                )

            # Other validation errors
            raise ValueError("Invalid GitQueryDict dictionary provided.")
    else:
        raise ValueError(
            f"Invalid repo input. Must be GitQuery string or GitQueryDict dict, but is: {repo} of type {type(repo)}"
        )

    return parsed


@typecheck
def extract_url(repo: str | GitQuery | GitQueryDict) -> str:
    """
    Extract the URL from a string. If any string other than a GitQuery is given, it is returned as-is.

    :param repo: Git repository URL, GitQuery string, or GitQueryDict dictionary
    :type repo: str | GitQuery | GitQueryDict
    :return: URL without query parameters
    :rtype: str
    """
    return parse_git_query(repo)["url"]


@typecheck
def edit_url(url: str, **kwargs) -> str:
    """
    Add, update, or remove query parameters in a URL.

    :param url: Original URL
    :type url: str
    :param kwargs: Query parameters to add/update (key=value) or remove (key=None)
    :return: Modified URL with updated query parameters
    :rtype: str
    :raises ValueError: If the input kwargs are invalid
    """
    if not full_isinstance(kwargs, dict[str, str | None]):
        raise ValueError(
            f"All keys in kwargs must be strings and values "
            f"must be strings or None, but got: {kwargs}"
        )

    parts = urlparse(url)
    query = parse_qs(parts.query)

    for key, value in kwargs.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = [value]

    new_query = urlencode(query, doseq=True, quote_via=quote, safe="/")
    parts = parts._replace(query=new_query)
    return urlunparse(parts)


@cache
@typecheck
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
