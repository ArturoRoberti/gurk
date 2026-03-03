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

from packaging.version import InvalidVersion, Version

from .types import PytestInputException


def bump_patch(version_str: str) -> str:
    """
    Bump the patch version of a version string (e.g., "1.0.0" -> "1.0.1").

    :param version_str: The version string to bump
    :type version_str: str
    :return: The bumped version string
    :rtype: str
    """
    # Get release components (major, minor, patch)
    try:
        v = Version(version_str)
    except InvalidVersion:
        raise PytestInputException(
            f"Invalid version string '{version_str}' provided for bumping."
        )

    # Return new version string with incremented patch
    return f"{v.major}.{v.minor}.{v.micro + 1}"
