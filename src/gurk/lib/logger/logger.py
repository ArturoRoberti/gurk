import shutil
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import IO, Any

from rich import print as richprint
from rich.console import Console
from rich.progress import (
    BarColumn,
    Live,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm, Prompt

from gurk.lib.utils.common import NO_ANSWERS, YES_ANSWERS

from .utils import LoggerEnum, LoggerSeverity, TaskInfos, TaskTerminationType


@dataclass
class Logger:
    """Logger with progress tracking and rich-formatted output."""

    # fmt: off
    verbose:         bool      = field()
    non_interactive: bool      = field()

    logdir:          Path      = field(init=False)
    task_infos:      TaskInfos = field(init=False, repr=False, default_factory=dict)

    _tasks_lock:     Lock      = field(init=False, repr=False, default_factory=Lock)
    _console_out:    Console   = field(init=False, repr=False)
    _console_err:    Console   = field(init=False, repr=False)
    _progress:       Progress  = field(init=False, repr=False)
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
            / ".gurk"
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

        safe_name = task_name.replace("/", "_")
        dest = self.logdir / "modified_scripts" / f"{safe_name}.{ext}"
        shutil.copy2(script, dest)
        self.debug(
            f"Logged modified script for task '{task_name}' to '{dest.as_posix()}'"
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

    def generate_logfile_path(self, task_id: TaskID) -> Path | None:
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

            safe_name = task_info["name"].replace("/", "_")
            logfile = self.logdir / f"{safe_name}.log"
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
            raise SystemExit(0)
        elif severity == LoggerSeverity.FATAL:
            raise SystemExit(1)

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
        :raises ValueError: If an unknown task termination type is provided
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
    def richprint(
        message: str, color: str | None = None, file: IO[str] | None = None
    ) -> None:
        """
        Print a rich-formatted message with optional color.

        :param message: The message to print
        :type message: str
        :param color: Optional color for the message
        :type color: str | None
        :param file: The output file (stdout/stderr). If None, defaults to stdout.
        :type file: IO[str] | None
        """
        if color:
            richprint(f"[{color}]{message}[/{color}]", file=file)
        else:
            richprint(message, file=file)

    @staticmethod
    def logrichprint(
        severity: LoggerSeverity | None,
        message: str,
        file: IO[str] | None = None,
    ) -> None:
        """
        Print a rich-formatted log message with the specified severity.

        :param severity: Severity level
        :type severity: LoggerSeverity | None
        :param message: The message to print
        :type message: str
        :param file: The output file (stdout/stderr). If None, defaults to stdout.
        :type file: IO[str] | None
        """
        if severity is None:
            richprint(f"{message}", file=file)
        else:
            logstart = Logger.logstart(severity)
        richprint(f"{logstart} {message}", file=file)

    @staticmethod
    def padded_print(
        text: str,
        color: str = "white",
        total_length: int = 128,
        top: bool = True,
        bottom: bool = True,
        file: IO[str] | None = None,
    ) -> None:
        """
        Print text padded with "=" signs to center it within a specified total length.

        :param text: Text to be printed
        :type text: str
        :param color: Color of the text
        :type color: str
        :param total_length: Total length of the printed line including padding
        :type total_length: int
        :param top: Whether to print the top padding line
        :type top: bool
        :param bottom: Whether to print the bottom padding line
        :type bottom: bool
        :param file: The output file (stdout/stderr). If None, defaults to stdout.
        :type file: IO[str] | None
        """
        # Top bar
        if top:
            Logger.richprint("=" * total_length, color=color, file=file)

        # Calculate how many "=" signs are needed in the middle
        #   Subtract 2 for extra spaces
        remaining_length = total_length - len(text) - 2
        if remaining_length < 0:
            Logger.richprint(f"{text}", color=color, file=file)
        else:
            left_pad = remaining_length // 2
            right_pad = remaining_length - left_pad
            Logger.richprint(
                f"{'=' * left_pad} {text} {'=' * right_pad}",
                color=color,
                file=file,
            )
        # Bottom bar
        if bottom:
            Logger.richprint("=" * total_length, color=color, file=file)

    @staticmethod
    def pprint_dict(
        dct: dict[str, Any],
        *,
        color: str = "white",
        capitalize: bool = False,
        indent: int = 0,
        indent_step: int = 2,
    ) -> None:
        """
        Pretty-print a dictionary of arbitrary depth with aligned keys and colored output.

        :param dct: Dictionary to pretty-print
        :param color: Color name for the keys
        :param capitalize: Whether to capitalize string keys
        :param indent: Base indentation (spaces)
        :param indent_step: Spaces added per nesting level
        """

        if not isinstance(dct, dict):
            richprint(f"{' ' * indent}{dct}")
            return

        maxlen = max((len(str(k)) for k in dct), default=0)

        for k, v in dct.items():
            key = k.capitalize() if capitalize and isinstance(k, str) else k
            pad = " " * indent
            msg = f"{pad}[{color}]{key:<{maxlen}}:[/{color}]"
            if not v:
                msg += f" {repr(v)}"
                richprint(msg)
                continue

            if isinstance(v, dict):
                richprint(msg)
                Logger.pprint_dict(
                    v,
                    color=color,
                    capitalize=capitalize,
                    indent=indent + indent_step,
                    indent_step=indent_step,
                )

            elif isinstance(v, (list, tuple, set)):
                richprint(msg)
                for item in v:
                    if isinstance(item, dict):
                        Logger.pprint_dict(
                            item,
                            color=color,
                            capitalize=capitalize,
                            indent=indent + indent_step,
                            indent_step=indent_step,
                        )
                    else:
                        richprint(f"{' ' * (indent + indent_step)}- {item}")

            else:
                richprint(f"{msg} {v}")

    @staticmethod
    def newline() -> None:
        """Print a newline to the console output."""
        richprint("")

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

    @property
    def can_prompt(self) -> bool:
        """
        Check if the logger can prompt the user for input.

        :return: True if interactive and console is a terminal, False otherwise
        :rtype: bool
        """
        return not self.non_interactive and self._console_out.is_terminal

    @contextmanager
    def _suspend_progress(self):
        """Context manager to temporarily suspend the progress display."""
        live: Live | None = getattr(self._progress, "live", None)
        if live and live.is_started:
            live.stop()
            try:
                yield
            finally:
                live.start()
        else:
            yield

    def prompt_bool(self, message: str, answer: str | bool = None) -> bool:
        """
        Prompt the user for a yes/no response.

        :param message: The prompt message.
        :type message: str
        :param answer: Predefined answer for non-interactive mode (True/False for 'y'/'n').
        :type answer: bool | None
        :return: True if the user responds with 'y', False for 'n'.
        :rtype: bool
        :raises RuntimeError: If in non-interactive mode without a predefined answer.
        :raises ValueError: If the predefined answer is invalid.
        """
        # Non-interactive mode
        if not self.can_prompt and answer is None:
            raise RuntimeError(
                "Cannot prompt for input in non-interactive mode without a predefined answer."
            )

        # Automatic answer handling
        if answer is not None:
            if isinstance(answer, bool):
                return answer
            elif isinstance(answer, str):
                answer = answer.strip().lower()
                if answer in YES_ANSWERS:
                    return True
                elif answer in NO_ANSWERS:
                    return False
                else:
                    raise ValueError(
                        f"Invalid predefined answer string '{answer}'"
                    )
            else:
                raise ValueError(
                    f"Invalid predefined answer type '{type(answer)}'"
                )
        elif not self.can_prompt:
            # Non-interactive mode without predefined answer defaults to 'no'
            return False

        # Interactive prompt
        with self._suspend_progress():
            return Confirm.ask(message)

    def ask(self, message: str, password: bool = False) -> str:
        """
        Prompt the user for input.

        :param message: The prompt message.
        :type message: str
        :param password: Whether to mask the input (for passwords).
        :type password: bool
        :return: The user's input.
        :rtype: str
        :raises RuntimeError: If in non-interactive mode.
        """
        # Non-interactive mode
        if not self.can_prompt:
            raise RuntimeError(
                "Cannot prompt for input in non-interactive mode."
            )

        # Interactive prompt
        with self._suspend_progress():
            return Prompt.ask(
                f"{message}", console=self._console_out, password=password
            )
