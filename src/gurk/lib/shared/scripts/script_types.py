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
from typing import TypedDict


class _ScriptExtension(Enum):
    """Enumeration of supported script file extensions."""

    # fmt: off
    BASH   = "bash"
    PYTHON = "py"
    # fmt: on


class ScriptBlockTypes(Enum):
    """Types of top-level script blocks."""

    # fmt: off
    CLASS      = auto()
    FUNCTION   = auto()
    ENTRYPOINT = auto()
    IMPORT     = auto()
    OTHER      = auto()
    # fmt: on

    def __repr__(self):
        return self.name


class ScriptBlock(TypedDict):
    """Information about a top-level script block."""

    # fmt: off
    type:  ScriptBlockTypes
    name:  str | None
    lines: tuple[int, int]  # (start_line, end_line)
    # fmt: on
