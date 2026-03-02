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

from typing import TypedDict, get_type_hints

from gurk.lib.utils import GIT_QUERY_VERSIONING_FIELDS

from .exceptions import PytestUnexpectedException


class VersioningExistence(TypedDict):
    # fmt: off
    exists:  str
    missing: str
    # fmt: on


class PluginVersioning(TypedDict):
    version: VersioningExistence
    branch: VersioningExistence
    commit: VersioningExistence


# Check that all versioning fields have the required exist/missing structure
for field in GIT_QUERY_VERSIONING_FIELDS:
    if field not in get_type_hints(PluginVersioning).keys():
        raise PytestUnexpectedException(
            f"Versioning field '{field}' is missing from the 'PluginVersioning' "
            f"TypedDict - please add it to the class definition in {__file__}."
        )
