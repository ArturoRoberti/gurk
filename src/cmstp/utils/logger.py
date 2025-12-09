from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, TypedDict, Union

from rich.progress import TaskID


@dataclass(frozen=True)
class LoggerTextSpec:
    # fmt: off
    label:  str
    color:  str
    bold:   bool
    bright: bool
    # fmt: on


class LoggerEnumBase(Enum):
    value: LoggerTextSpec

    @property
    def label(self):
        return self.value.label

    @property
    def color(self):
        return self.value.color

    @property
    def bold(self):
        return self.value.bold

    @property
    def bright(self):
        return self.value.bright


class LoggerTaskTerminationType(LoggerEnumBase):
    # fmt: off
    SUCCESS = LoggerTextSpec("Success", "green" , False, False)
    FAILURE = LoggerTextSpec("Failure", "red"   , False, False)
    SKIPPED = LoggerTextSpec("Skipped", "yellow", False, False)
    PARTIAL = LoggerTextSpec("Partial", "orange", False, False)
    # fmt: on


class LoggerSeverity(LoggerEnumBase):
    # fmt: off
    DEBUG   = LoggerTextSpec(" DEBUG ", "cyan",    False, False)
    INFO    = LoggerTextSpec("  INFO ", "blue",    False, False)
    WARNING = LoggerTextSpec("WARNING", "orange1", False, False)
    ERROR   = LoggerTextSpec(" ERROR ", "red",     False, False)
    FATAL   = LoggerTextSpec(" FATAL ", "red",     True , True )
    DONE    = LoggerTextSpec("  DONE ", "purple",  True , False)
    # fmt: on


LoggerEnum = Union[LoggerSeverity, LoggerTaskTerminationType]


# TODO: Maybe organize better / replace?
class TaskInfo(TypedDict):
    # fmt: off
    name:      str
    total:     int
    completed: int
    logfile:   Optional[Path]
    # fmt: on


TaskInfos = Dict[TaskID, TaskInfo]
