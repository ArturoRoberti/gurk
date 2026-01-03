import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

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
    TaskInfos,
    TaskTerminationType,
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

    def create_log_dir(self) -> None:
        """Create the log directory if it does not exist."""
        self.logdir.mkdir(parents=True, exist_ok=True)
        if self.verbose:
            script_logdir = self.logdir / "modified_scripts"
            script_logdir.mkdir(parents=True, exist_ok=True)

    def log_script(self, script: Path, task_name: str, ext: str) -> None:
        """
        Save the given script to the log directory under 'modified_scripts'.

        :param script: Content of the script to log
        :type script: Path
        :param task_name: Name of the script file
        :type task_name: str
        :param ext: Extension of the script file (e.g., 'bash', 'py')
        :type ext: str
        """
        if not self.verbose:
            # Don't log scripts if not in verbose mode
            return

        shutil.copy2(
            script, self.logdir / "modified_scripts" / f"{task_name}.{ext}"
        )

    def add_task(self, task_name: str, total: int = 1) -> TaskID:
        """
        Add a new task to the progress tracker.

        :param task_name: Name of the task
        :type task_name: str
        :param total: Total number of steps for the task
        :type total: int
        :return: The ID of the created task
        :rtype: TaskID
        """
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
        """
        Generate a logfile path for a given task name.

        :param task_id: ID of the task
        :type task_id: TaskID
        :return: The path to the logfile, or None if task not found
        :rtype: Path | None
        """
        with self._tasks_lock:
            if task_id not in self.task_infos:
                return None
            task_info = self.task_infos[task_id]

            logfile = self.logdir / f"{task_info['name']}.log"
            task_info["logfile"] = logfile

        return logfile

    def set_total(self, task_id: TaskID, total: int) -> None:
        """
        Set the total number of steps for a task, in case it was unknown at creation.

        :param task_id: ID of the task
        :type task_id: TaskID
        :param total: Total number of steps for the task
        :type total: int
        """
        with self._tasks_lock:
            if task_id in self.task_infos:
                self.task_infos[task_id]["total"] = total
        self._progress.update(task_id, total=total)

    def update_task(
        self, task_id: TaskID, message: str, advance: bool = True
    ) -> None:
        """
        Update the progress of a task, optionally advancing it by one step.

        :param task_id: ID of the task
        :type task_id: TaskID
        :param message: Description message for the task update
        :type message: str
        :param advance: Whether to advance the task progress by one step
        :type advance: bool
        """
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

        :param severity: Severity level
        :type severity: LoggerEnum
        :return: The rich-formatted color string
        :rtype: str
        """
        return f"{'bold 'if severity.bold else ''}{'bright_'if severity.bright else ''}{severity.color}"

    @staticmethod
    def logstart(severity: LoggerEnum) -> str:
        """
        Generate a rich-formatted severity tag for logging.

        :param severity: Severity level
        :type severity: LoggerEnum
        :return: The rich-formatted severity tag
        :rtype: str
        """
        color = Logger.logcolor(severity)
        return f"[{color}][{severity.label}][/{color}]"

    def log(
        self,
        severity: LoggerSeverity,
        message: str,
        syntax_highlight: bool = True,
    ) -> None:
        """
        Log a message with the specified severity.
            If severity is ERROR or FATAL, log to stderr.
            If severity is FATAL, exit the program after logging.

        :param severity: Severity level
        :type severity: LoggerSeverity
        :param message: The message to log
        :type message: str
        :param syntax_highlight: Whether to apply syntax highlighting
        :type syntax_highlight: bool
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

    def debug(self, message: str, syntax_highlight: bool = True) -> None:
        """Log a debug message. See Logger.log for details."""
        self.log(LoggerSeverity.DEBUG, message, syntax_highlight)

    def info(self, message: str, syntax_highlight: bool = True) -> None:
        """Log an info message. See Logger.log for details."""
        self.log(LoggerSeverity.INFO, message, syntax_highlight)

    def warning(self, message: str, syntax_highlight: bool = True) -> None:
        """Log a warning message. See Logger.log for details."""
        self.log(LoggerSeverity.WARNING, message, syntax_highlight)

    def error(self, message: str, syntax_highlight: bool = True) -> None:
        """Log an error message. See Logger.log for details."""
        self.log(LoggerSeverity.ERROR, message, syntax_highlight)

    def fatal(self, message: str, syntax_highlight: bool = True) -> None:
        """Log a fatal message and exit. See Logger.log for details."""
        self.log(LoggerSeverity.FATAL, message, syntax_highlight)

    def done(self, message: str, syntax_highlight: bool = True) -> None:
        """Log a done message. See Logger.log for details."""
        self.log(LoggerSeverity.DONE, message, syntax_highlight)

    def finish_task(
        self,
        task_id: int,
        success: TaskTerminationType,
    ) -> None:
        """
        Mark a task as finished, updating its progress and description.

        :param task_id: ID of the task
        :type task_id: int
        :param success: Task termination type indicating how the task completed
        :type success: TaskTerminationType
        """
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

        if success == TaskTerminationType.SUCCESS:
            symbol = "✔"
        elif success == TaskTerminationType.PARTIAL:
            symbol = "⚠"
        elif success == TaskTerminationType.SKIPPED:
            symbol = "⊘"
        elif success == TaskTerminationType.FAILURE:
            symbol = "✖"
        else:
            raise ValueError("Unknown task termination type")
        desc = f"[{success.color}]{symbol} {success.label}: {task_name}[/{success.color}]"
        if logfile:
            desc += f" [blue](log: {logfile})[/blue]"
        self._progress.update(task_id, completed=total, description=desc)

    @staticmethod
    def richprint(message: str, color: Optional[str] = None) -> None:
        """
        Print a rich-formatted message with optional color.

        :param message: The message to print
        :type message: str
        :param color: Optional color for the message
        :type color: Optional[str]
        """
        if color:
            richprint(f"[{color}]{message}[/{color}]")
        else:
            richprint(message)

    @staticmethod
    def logrichprint(
        severity: LoggerSeverity, message: str, newline: bool = False
    ) -> None:
        """
        Print a rich-formatted log message with the specified severity.

        :param severity: Severity level
        :type severity: LoggerSeverity
        :param message: The message to print
        :type message: str
        :param newline: Whether to print a newline before the message
        :type newline: bool
        """
        logstart = Logger.logstart(severity)
        prefix = "\n" if newline else ""
        richprint(f"{prefix}{logstart} {message}")

    @staticmethod
    def step(message: str, warning: bool = False) -> None:
        """
        Log a step message indicating progress. Only to be used from within tasks.

        :param message: Message to log
        :type message: str
        :param warning: Whether or not this is a warning (default: false)
        :type warning: bool
        :param progress: Whether to progress the task
        :type progress: bool
        """
        step_type = "STEP_NO_PROGRESS"
        if warning:
            step_type += "_WARNING"
        print(f"\n__{step_type}__: {message}")
