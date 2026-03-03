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

from pathlib import Path
from typing import TypeAlias, TypedDict

from .args import ResolvedArgsDefinitionCollection


class ResolvedDefaultTaskDict(TypedDict):
    """Dictionary representing a resolved default task configuration."""

    # fmt: off
    description:    str
    script:         Path
    function:       None | str
    config_file:    None | Path
    depends_on:     list[str]
    privileged:     bool
    supercedes:     list[str]
    args:           ResolvedArgsDefinitionCollection
    # fmt: on


ResolvedDefaultTaskDictCollection: TypeAlias = dict[
    str, ResolvedDefaultTaskDict
]
