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

from typing import NotRequired, TypeAlias, TypedDict

from .args import ArgsDefinitionCollection


class DefaultTaskDict(TypedDict):
    """Dictionary representing a default task configuration."""

    # fmt: off
    description:    str
    script:         str
    function:       None | str
    config_file:    NotRequired[None | str]
    depends_on:     NotRequired[list[str]]
    privileged:     NotRequired[bool]
    supercedes:     NotRequired[list[str]]
    args:           NotRequired[ArgsDefinitionCollection]
    # fmt: on


DefaultTaskDictCollection: TypeAlias = dict[str, DefaultTaskDict]
