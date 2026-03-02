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

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class LoggerTextSpec:
    """
    Text specification for logger enums.

    :NOTE: Not all colors support additional tweaks such as "bold" or "bright"
           (etc.). Look at all available colors via the rich.color.ANSI_COLOR_NAMES
           list (`from rich.color import ANSI_COLOR_NAMES; print(ANSI_COLOR_NAMES)`)
    """

    # fmt: off
    label:  str
    color:  str
    bold:   bool
    bright: bool
    # fmt: on


class _LoggerEnumBase(Enum):
    """
    Base class for logger enums with text specifications.
    """

    value: LoggerTextSpec

    @property
    def label(self) -> str:
        return self.value.label

    @property
    def color(self) -> str:
        return self.value.color

    @property
    def bold(self) -> bool:
        return self.value.bold

    @property
    def bright(self) -> bool:
        return self.value.bright


class TaskTerminationType(_LoggerEnumBase):
    """
    Types of task termination statuses.
    """

    # fmt: off
    SUCCESS = LoggerTextSpec("Success", "green"  , False, False)
    FAILURE = LoggerTextSpec("Failure", "red"    , False, False)
    SKIPPED = LoggerTextSpec("Skipped", "yellow" , False, False)
    PARTIAL = LoggerTextSpec("Partial", "orange1", False, False)
    # fmt: on


class LoggerSeverity(_LoggerEnumBase):
    """
    Severity levels for logging messages.
    """

    # fmt: off
    DEBUG   = LoggerTextSpec(" DEBUG ", "cyan",    False, False)
    INFO    = LoggerTextSpec("  INFO ", "blue",    False, False)
    WARNING = LoggerTextSpec("WARNING", "orange1", False, False)
    ERROR   = LoggerTextSpec(" ERROR ", "red",     False, False)
    SUCCESS = LoggerTextSpec("SUCCESS", "green",   True , False)
    FATAL   = LoggerTextSpec(" FATAL ", "red",     True , True )
    DONE    = LoggerTextSpec("  DONE ", "purple",  True , False)
    # fmt: on
