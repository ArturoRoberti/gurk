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

from typing import NotRequired, TypeAlias, TypedDict, Union


class ArgsDefinition(TypedDict):
    """Dictionary representing argument definitions for tasks."""

    # fmt: off
    help:        str
    default:     NotRequired[None | bool | str | list[str]]
    choices:     NotRequired[None | list[str]]
    nargs:       NotRequired[None | Union[int, str]]
    mutex:       NotRequired[None | str]
    # fmt: on


ArgsDefinitionCollection: TypeAlias = dict[str, ArgsDefinition]
