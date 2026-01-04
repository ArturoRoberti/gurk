from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, TypedDict, TypeVar

from rich.progress import TaskID


@dataclass(frozen=True)
class LoggerTextSpec:
    """
    Text specification for logger enums.

    NOTE: Not all colors support additional tweaks such as "bold" or "bright" (etc.). Look at all available colors
          via the rich.color.ANSI_COLOR_NAMES list (from rich.color import ANSI_COLOR_NAMES; print(ANSI_COLOR_NAMES))
    """

    # fmt: off
    label:  str
    color:  str
    bold:   bool
    bright: bool
    # fmt: on


class LoggerEnumBase(Enum):
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


class TaskTerminationType(LoggerEnumBase):
    """
    Types of task termination statuses.
    """

    # fmt: off
    SUCCESS = LoggerTextSpec("Success", "green"  , False, False)
    FAILURE = LoggerTextSpec("Failure", "red"    , False, False)
    SKIPPED = LoggerTextSpec("Skipped", "yellow" , False, False)
    PARTIAL = LoggerTextSpec("Partial", "orange1", False, False)
    # fmt: on


class LoggerSeverity(LoggerEnumBase):
    """
    Severity levels for logging messages.
    """

    # fmt: off
    DEBUG   = LoggerTextSpec(" DEBUG ", "cyan",    False, False)
    INFO    = LoggerTextSpec("  INFO ", "blue",    False, False)
    WARNING = LoggerTextSpec("WARNING", "orange1", False, False)
    ERROR   = LoggerTextSpec(" ERROR ", "red",     False, False)
    FATAL   = LoggerTextSpec(" FATAL ", "red",     True , True )
    DONE    = LoggerTextSpec("  DONE ", "purple",  True , False)
    # fmt: on


LoggerEnum = TypeVar("LoggerEnum", bound=LoggerEnumBase)


class TaskInfo(TypedDict):
    """
    Information about a logged task.
    """

    # fmt: off
    name:      str
    total:     int
    completed: int
    logfile:   Optional[Path]
    # fmt: on


TaskInfos = Dict[TaskID, TaskInfo]
