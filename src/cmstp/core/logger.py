import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from rich import print as richprint
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from cmstp.utils.logger import (
    LoggerEnum,
    LoggerSeverity,
    LoggerTaskTerminationType,
    TaskInfos,
)


@dataclass
class Logger:
    """Logger with progress tracking and rich-formatted output."""

    # fmt: off
    verbose:      bool      = field()

    logdir:       Path      = field(init=False)
    task_infos:   TaskInfos = field(init=False, repr=False, default_factory=dict)

    _tasks_lock:  Lock      = field(init=False, repr=False, default_factory=Lock)
    _console_out: Console   = field(init=False, repr=False)
    _console_err: Console   = field(init=False, repr=False)
    _progress:    Progress  = field(init=False, repr=False)

    # Used only in testing  # TODO: Use
    _failed_tasks: Dict[str, Optional[Path]] = field(init=False, repr=False, default_factory=dict)
    # fmt: on

    def __post_init__(self):
        self._console_out = Console(log_path=False, log_time=False)
        self._console_err = Console(
            log_path=False, log_time=False, stderr=True
        )
        self._progress = Progress(
            TimeElapsedColumn(),
            BarColumn(),
            TextColumn("{task.description}"),
            console=self._console_out,
        )
        self.logdir = (
            Path.home()
            / ".cmstp"
            / "logs"
            / datetime.now().strftime("%Y%m%d_%H%M%S")
        )

    def __enter__(self):
        self._progress.__enter__()  # start live-render
        return self

    def __exit__(self, exc_type, exc, tb):
        self._progress.__exit__(exc_type, exc, tb)  # stop live-render
        return False  # propagate exceptions

    def create_log_dir(self):
        """Create the log directory if it does not exist."""
        self.logdir.mkdir(parents=True, exist_ok=True)

    def add_task(self, task_name: str, total: int = 1) -> TaskID:
        """Add a new task to the progress tracker."""
        task_id = self._progress.add_task(
            f"{task_name}: starting", total=total
        )
        self._progress.update(
            task_id, description=f"[yellow]⚡Started: {task_name}"
        )
        with self._tasks_lock:
            self.task_infos[task_id] = {
                "name": task_name,
                "total": total or 0,
                "completed": 0,
                "logfile": None,
            }
        return task_id

    def generate_logfile_path(self, task_id: TaskID) -> Optional[Path]:
        """Generate a logfile path for a given task name."""
        with self._tasks_lock:
            if task_id not in self.task_infos:
                return None
            task_info = self.task_infos[task_id]

            logfile = self.logdir / f"{task_info['name']}.log"
            task_info["logfile"] = logfile

        return logfile

    def set_total(self, task_id: TaskID, total: int):
        """Set the total number of steps for a task."""
        with self._tasks_lock:
            if task_id in self.task_infos:
                self.task_infos[task_id]["total"] = total
        self._progress.update(task_id, total=total)

    def update_task(self, task_id: TaskID, message: str, advance: bool = True):
        """Update the progress of a task, optionally advancing it by one step."""
        with self._tasks_lock:
            if task_id not in self.task_infos:
                return
            task_info = self.task_infos[task_id]

            task_name = task_info["name"]
            if (
                advance and task_info["completed"] < task_info["total"] - 1
            ):  # Prevent finihing/over-advancing
                self._progress.advance(task_id, 1)
                task_info["completed"] += 1

        self._progress.update(
            task_id, description=f"[cyan]▸ Running: {task_name} - {message}"
        )

    @staticmethod
    def logcolor(severity: LoggerEnum) -> str:
        """
        Generate a rich-formatted color string for the given severity.

        NOTE: Not all colors support additional tweaks such as "bold" or "bright" (etc.). Look at all available colors
              via the rich.color.ANSI_COLOR_NAMES list (from rich.color import ANSI_COLOR_NAMES; print(ANSI_COLOR_NAMES))
        """
        return f"{'bold 'if severity.bold else ''}{'bright_'if severity.bright else ''}{severity.color}"

    @staticmethod
    def logstart(severity: LoggerEnum) -> str:
        """
        Generate a rich-formatted severity tag for logging.

        NOTE: Not all colors support additional tweaks such as "bold" or "bright" (etc.). Look at all available colors
              via the rich.color.ANSI_COLOR_NAMES list (from rich.color import ANSI_COLOR_NAMES; print(ANSI_COLOR_NAMES))
        """
        color = Logger.logcolor(severity)
        return f"[{color}][{severity.label}][/{color}]"

    def log(
        self,
        severity: LoggerSeverity,
        message: str,
        syntax_highlight: bool = True,
    ):
        """
        Log a message with the specified severity.
        If severity is ERROR or FATAL, log to stderr.
        If severity is FATAL, exit the program after logging.
        """
        if severity == LoggerSeverity.DEBUG and not self.verbose:
            return
        elif severity in (LoggerSeverity.ERROR, LoggerSeverity.FATAL):
            console = self._console_err
        else:
            console = self._console_out

        lines = message.splitlines()
        if lines:
            # First line: include the severity tag
            console.log(
                f"{self.logstart(severity)} {lines[0]}",
                highlight=syntax_highlight,
            )
            # Remaining lines: indent under the tag
            for line in lines[1:]:
                console.log(
                    f"{' ' * (len(severity.label) + 3)}{line}",
                    highlight=syntax_highlight,
                )  # +3 accounts for the brackets and space

        if severity == LoggerSeverity.DONE:
            sys.exit(0)
        elif severity == LoggerSeverity.FATAL:
            sys.exit(1)

    def debug(self, message: str, syntax_highlight: bool = True):
        """Log a debug message."""
        self.log(LoggerSeverity.DEBUG, message, syntax_highlight)

    def info(self, message: str, syntax_highlight: bool = True):
        """Log an info message."""
        self.log(LoggerSeverity.INFO, message, syntax_highlight)

    def warning(self, message: str, syntax_highlight: bool = True):
        """Log a warning message."""
        self.log(LoggerSeverity.WARNING, message, syntax_highlight)

    def error(self, message: str, syntax_highlight: bool = True):
        """Log an error message."""
        self.log(LoggerSeverity.ERROR, message, syntax_highlight)

    def fatal(self, message: str, syntax_highlight: bool = True):
        """Log a fatal message and exit."""
        self.log(LoggerSeverity.FATAL, message, syntax_highlight)

    def done(self, message: str, syntax_highlight: bool = True):
        """Log a done message."""
        self.log(LoggerSeverity.DONE, message, syntax_highlight)

    def finish_task(
        self,
        task_id: int,
        success: bool,
    ):
        """Mark a task as finished, updating its progress and description."""
        with self._tasks_lock:
            if task_id not in self.task_infos:
                return
            task_info = self.task_infos[task_id]

            total = task_info["total"]
            if task_info.get("completed", 0) >= total:
                # If already marked as completed, don't update again
                return
            task_info["completed"] = total

            logfile = task_info["logfile"]
            task_name = task_info["name"]

        if success:  # TODO: Expand to more than boolean
            symbol = "✔"
            termination_type = LoggerTaskTerminationType.SUCCESS
        else:
            symbol = "✖"
            termination_type = LoggerTaskTerminationType.FAILURE
            self._failed_tasks[task_name] = logfile
        desc = f"[{termination_type.color}]{symbol} {termination_type.label}: {task_name}[/{termination_type.color}]"
        if logfile:
            desc += f" [blue](log: {logfile})[/blue]"
        self._progress.update(task_id, completed=total, description=desc)

    @staticmethod
    def richprint(message: str, color: Optional[str] = None):
        if color:
            richprint(f"[{color}]{message}[/{color}]")
        else:
            richprint(message)

    @staticmethod
    def logrichprint(
        severity: LoggerSeverity, message: str, newline: bool = False
    ):
        """Print a rich-formatted log message with the specified severity."""
        logstart = Logger.logstart(severity)
        prefix = "\n" if newline else ""
        richprint(f"{prefix}{logstart} {message}")

    @staticmethod
    def step(message: str, progress: bool = False):
        """Log a step message indicating progress."""
        print(f"\n__STEP{'_NO_PROGRESS' if not progress else ''}__: {message}")
