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

from enum import Enum, auto
from typing import TypeAlias

from gurk.lib.utils import PathLike

from ..remotes import GitQuery

PluginSource: TypeAlias = PathLike | GitQuery
PluginSpecification: TypeAlias = str | PluginSource


class PluginSpecificationEnum(Enum):
    # fmt: off
    LOCAL_PATH  = auto()
    GIT_REMOTE  = auto()
    PLUGIN_NAME = auto()
    # fmt: on
