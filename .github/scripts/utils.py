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

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
PLUGIN_FOLDER_PREFIX = "src/gurk/plugins/"
DEFAULT_BRANCH = "origin/main"


def get_git_diff(
    path: str | Path | None = None,
    name_only: bool = False,
    staged: bool = True,
    ref: str = DEFAULT_BRANCH,
) -> str:
    """
    Get the git diff between the specified reference and the current HEAD.

    :param path: Optional path to get the diff for/under.
    :type path: str | Path | None
    :param name_only: Whether to return only the names of changed files
    :type name_only: bool
    :param staged: Whether to include staged changes
    :type staged: bool
    :param ref: The git reference to compare against
    :type ref: str
    :return: The git diff as a string
    :rtype: str
    """
    diff_cmd = [
        "git",
        "diff",
        "--unified=0",
        "--ignore-space-change",
        ref,
    ]
    if path:
        diff_cmd.extend(["--", str(path)])
    if name_only:
        diff_cmd.insert(2, "--name-only")
    if staged:
        diff_cmd.insert(2, "--staged")

    return subprocess.check_output(diff_cmd, text=True)
