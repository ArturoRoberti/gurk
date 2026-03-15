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

from enum import Enum


class RegistryKind(Enum):
    """Represents the kind of registry to use for a plugin specification."""

    # fmt: off
    PUBLIC  = 0
    PRIVATE = 1
    # fmt: on


class ExpectedOutcome(Enum):
    """Represents the expected outcome of a test case as (exit_code, contains_errors)."""

    SUCCESS = (0, False)
    PARTIAL = (0, True)
    FAILURE = (1, True)
    ARGPARSE = (2, True)  # argparse error

    @property
    def exit_code(self) -> int:
        return self.value[0]

    @property
    def contains_errors(self) -> bool:
        return self.value[1]
