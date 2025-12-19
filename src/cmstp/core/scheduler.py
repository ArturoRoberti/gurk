import json
import os
import pty
import subprocess
import termios
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Event, Lock, Thread
from typing import Dict, List, Optional, Set, TextIO, Tuple

from cmstp.core.logger import Logger
from cmstp.utils.command import Command, CommandKind
from cmstp.utils.interface import run_script_function
from cmstp.utils.logger import TaskTerminationType
from cmstp.utils.patterns import PatternCollection
from cmstp.utils.system_info import get_system_info
from cmstp.utils.tasks import ResolvedTask


@dataclass
class Scheduler:
    """Schedules and runs tasks with dependencies, handling logging and progress tracking."""

    # fmt: off
    logger:    Logger             = field(repr=False)
    tasks:     List[ResolvedTask] = field(repr=False)
    askpass_file: str         = field(repr=False)

    results:   Dict[ResolvedTask, TaskTerminationType] = field(init=False, repr=False, default_factory=dict)
    scheduled: Set[ResolvedTask]                             = field(init=False, repr=False, default_factory=set)

    lock:      Lock  = field(init=False, repr=False, default_factory=Lock)
    queue:     Queue = field(init=False, repr=False, default_factory=Queue)
    # fmt: on

    @staticmethod
    def _prepare_script(command: Command) -> Tuple[Path, int]:
        """
        Prepare a copy of the desired script that
        - Uses STEP statements only if in the desired function (or entrypoint)
        - Converts all STEP comments into equivalent print statements.

        :param command: Command to prepare
        :type command: Command
        :return: Tuple of (path to modified script, number of steps)
        :rtype: Tuple[Path, int]
        """
        original_path = Path(command.script)
        tmp = NamedTemporaryFile(delete=False, suffix=f"_{original_path.name}")
        tmp_path = Path(tmp.name)
        tmp.close()

        start = None
        in_desired = False
        in_function = False
        in_entrypoint = False
        loc_indent = None
        function_name = None

        def detect_block_start(
            stripped: str, indent_len: int
        ) -> Optional[Tuple[str, Optional[str], int]]:
            """
            Detect the start of a function, class, or entrypoint block.

            :param stripped: The stripped line
            :type stripped: str
            :param indent_len: The indentation length of the line
            :type indent_len: int
            :return: Tuple of (kind, name, location_indent) or None
            :rtype: Tuple[str, str | None, int] | None
            """
            # TODO: Can this handle nested functions/classes?
            # Function
            r_func = PatternCollection[command.kind.name].patterns["blocks"][
                "FUNCTION"
            ]
            m_func = r_func.match(stripped)

            # Entrypoint
            r_entry = PatternCollection[command.kind.name].patterns[
                "entrypoints"
            ]
            m_entry = r_entry.match(stripped)

            # Class (for python)
            r_class = PatternCollection[command.kind.name].patterns["blocks"][
                "CLASS"
            ]
            m_class = r_class.match(stripped) if r_class else None

            if m_func or m_class:
                name = m_func.group(1) if m_func else None
                return "function", name, indent_len
            if m_entry:
                return "entrypoint", None, indent_len
            return None

        def block_end_reached(stripped: str, indent_len: int) -> bool:
            """
            Determine if the current line ends the current block.

            :param stripped: The stripped line
            :type stripped: str
            :param indent_len: The indentation length of the line
            :type indent_len: int
            :return: True if the current line ends the current block, False otherwise
            :rtype: bool
            """
            if command.kind == CommandKind.PYTHON:
                # For python: non-empty line with indent <= loc_indent and not a comment
                if (
                    stripped.strip()
                    and indent_len <= (loc_indent or 0)
                    and not stripped.startswith("#")
                ):
                    return True
                return False
            else:
                # For bash: closing brace ends the block
                # TODO: This only works for entrypoints if they are at the end of the script - Fix
                return stripped.strip() == "}"

        def get_step(line: str) -> Tuple[Optional[str], Optional[str]]:
            """
            Determine if a line marks a STEP output

            :param line: The line to check
            :type line: str
            :return: Tuple of (step message, step type). Step type is
                     "comment" for STEP comments or
                     "any" for (assumed) STEP print statements or
                     None if not a STEP line.
            :rtype: Tuple[str | None, str | None]
            """
            step_patterns = PatternCollection.STEP.patterns

            # See if it's a STEP comment
            m_comment = step_patterns["comment"](progress=True).match(line)
            if m_comment:
                return m_comment.group(1).strip(), "comment"

            # See if it's a STEP print statement - ASSUME any line containing __STEP__ is a print statement
            m_any = step_patterns["any"](progress=True).match(line)
            if m_any:
                return m_any.group(1).strip(), "any"

            return None, None

        def replace_potential_step(
            line: str, indent: str, in_desired: bool
        ) -> str:
            """
            Replace a STEP comment with print statements, preserving indentation.
            If not in_desired, remove the STEP comment.

            :param line: The line to process
            :type line: str
            :param indent: The indentation of the line
            :type indent: str
            :param in_desired: Whether the line is in the desired block
            :type in_desired: bool
            :return: The processed line
            :rtype: str
            """
            step, step_type = get_step(line)
            if step is None:
                # Not a STEP line, return as is
                return line

            if in_desired:
                if step_type == "comment":
                    # TODO: make safe, i.e. replace any " with ' (or similar)
                    # Replace STEP comments with print statements
                    step_msg = f"\\n__STEP__: {step}"
                    if command.kind == CommandKind.PYTHON:
                        msg = f'print(f"{step_msg}")'
                    else:
                        msg = f'printf "{step_msg}\\n"'

                    return f"{indent}{msg}\n"
                else:
                    # Leave (assumed) STEP print statements as is
                    return line
            else:
                # Remove STEP print statements
                return f"{indent}{'pass' if command.kind == CommandKind.PYTHON else ':'}\n"

        # Main processing loop
        with original_path.open(
            "r", encoding="utf-8", errors="replace"
        ) as src, tmp_path.open("w", encoding="utf-8") as dst:
            for line in src:
                stripped = line.lstrip()
                indent = line[: len(line) - len(stripped)]
                indent_len = len(indent)

                # Detect block starts (function/class/entrypoint)
                start = detect_block_start(line, indent_len)
                if start:
                    kind, name, loc_indent = start
                    dst.write(line)
                    if kind == "function":
                        in_function = True
                        in_entrypoint = False
                        function_name = name
                    else:
                        in_function = False
                        in_entrypoint = True
                        function_name = None
                    continue

                if (
                    command.function
                    and in_function
                    and function_name == command.function
                ) or (not command.function and in_entrypoint):
                    in_desired = True
                else:
                    in_desired = False
                dst.write(replace_potential_step(line, indent, in_desired))

                if (in_function or in_entrypoint) and block_end_reached(
                    line, indent_len
                ):
                    in_function = False
                    in_entrypoint = False
                    loc_indent = None
                    function_name = None

        # Count steps
        n_steps = 0
        with tmp_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                step, step_type = get_step(line)
                if step and step_type == "any":
                    n_steps += 1

        return tmp_path, n_steps

    def _spawn_and_stream(
        self, proc_cmd: List[str], flog: TextIO, task_id: int
    ) -> TaskTerminationType:
        """
        Spawn a subprocess and stream its output to the logfile and progress tracker.

        :param proc_cmd: Command to run
        :type proc_cmd: List[str]
        :param flog: Log file to write output to
        :type flog: TextIO
        :param task_id: ID of the task for progress tracking
        :type task_id: int
        :return: Task termination type (SUCCESS, FAILURE, PARTIAL)
        :rtype: TaskTerminationType
        """
        # 1. Initialize Event for PARTIAL status tracking
        warning_event = Event()

        # 2. Create the PTY master and slave file descriptors
        master_fd, slave_fd = pty.openpty()

        # 3. Define the single reader function for the PTY master
        def pty_reader(master_fd: int) -> None:
            """Reads lines from the single PTY master stream."""

            # Use os.fdopen in a 'with' block to guarantee closing the master_fd upon exit.
            with os.fdopen(master_fd, "rb", 0) as master_file:
                try:
                    while True:
                        raw_data = os.read(master_file.fileno(), 4096)
                        if not raw_data:
                            break

                        data = raw_data.decode("utf-8", errors="replace")

                        for line_raw in data.splitlines(keepends=True):
                            line = line_raw.rstrip("\n")

                            # Write to logfile
                            flog.write(line + "\n")
                            flog.flush()

                            # Extract STEP statements with progress
                            m_progress = PatternCollection.STEP.patterns[
                                "output"
                            ](progress=True).match(line)
                            if m_progress:
                                self.logger.update_task(
                                    task_id, m_progress.group(1).strip()
                                )

                            # Extract STEP statements without progress
                            m_no_progress = PatternCollection.STEP.patterns[
                                "output"
                            ](progress=False).match(line)
                            m_no_progress_warning = (
                                PatternCollection.STEP.patterns["output"](
                                    progress=False, warning=True
                                ).match(line)
                            )
                            if m_no_progress or m_no_progress_warning:
                                if m_no_progress_warning:
                                    match = m_no_progress_warning
                                    warning_event.set()
                                else:
                                    match = m_no_progress

                                self.logger.update_task(
                                    task_id,
                                    match.group(1).strip(),
                                    advance=False,
                                )

                except Exception as e:
                    self.logger.debug(f"PTY reader encountered an error: {e}")

        # 4. Define preexec function for session isolation and FD cleanup in child process
        def preexec_setup():
            """Creates a new session and closes the PTY master FD in child."""
            # Use os.setsid to become session leader and claim TTY control
            os.setsid()
            # Child closes the PTY master FD
            os.close(master_fd)

            # Set terminal parameters for unbuffered output
            try:
                attrs = termios.tcgetattr(slave_fd)
                attrs[1] = attrs[1] & ~termios.ECHO
                termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
            except termios.error:
                pass

        # 5. Define environment for usage with SUDO_ASKPASS
        def create_sudo_wrapper() -> str:
            """Create a temporary sudo wrapper script, to avoid having to use 'sudo -A' everywhere."""
            # Temporary directory
            wrapper_dir = Path(TemporaryDirectory().name)
            if not wrapper_dir.exists():
                wrapper_dir.mkdir(parents=True, exist_ok=True)

            # Temporary sudo wrapper script
            sudo_wrapper = wrapper_dir / "sudo"
            with open(sudo_wrapper, "w") as f:
                f.write(
                    """
                    #!/bin/sh
                    exec /usr/bin/sudo -A "$@"
                """
                )
            os.chmod(sudo_wrapper, 0o700)

            return wrapper_dir.as_posix()

        env = os.environ.copy()
        env["SUDO_ASKPASS"] = self.askpass_file
        env["PATH"] = f"{create_sudo_wrapper()}:{env.get('PATH', '')}"

        # 5. Spawn the process with PTY connections
        process = subprocess.Popen(
            proc_cmd,
            bufsize=0,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=preexec_setup,
            env=env,
            text=False,
        )

        # 6. Parent closes its reference to the PTY slave
        os.close(slave_fd)

        # 7. Start the single reader thread on the PTY master
        t_out = Thread(target=pty_reader, args=(master_fd,), daemon=True)
        t_out.start()

        # 8. Wait for process exit and clean up
        exit_code = process.wait()
        t_out.join()

        # 9. Final Termination Logic: Check status and PARTIAL event
        if exit_code != 0:
            return TaskTerminationType.FAILURE
        elif warning_event.is_set():
            return TaskTerminationType.PARTIAL
        else:
            return TaskTerminationType.SUCCESS

    def run_task(
        self,
        task: ResolvedTask,
        task_id: int,
    ) -> TaskTerminationType:
        """
        Run a single task, logging its output and tracking progress.

        :param task: The task to run
        :type task: ResolvedTask
        :param task_id: ID of the task for progress tracking
        :type task_id: int
        :return: Task termination type indicating success, failure, or partial completion
        :rtype: TaskTerminationType
        """
        # Prepare script with modified step statements
        modified_script, n_steps = self._prepare_script(task.command)
        self.logger.debug(
            f"Prepared modified script for task '{task.name}' at {modified_script} with {n_steps} steps"
        )
        self.logger.log_script(
            modified_script, task.name, ext=task.command.kind.ext
        )

        def safe_unlink(path: Optional[Path]) -> None:
            """
            Unlink files that may or may not have been unlinked yet

            :param path: Path to the file to unlink
            :type path: Optional[Path]
            """
            if path and isinstance(path, Path) and path.exists():
                try:
                    path.unlink()
                except Exception:
                    # Already unlinked
                    pass

        # Create args
        args = task.args + ("--system-info", json.dumps(get_system_info()))
        if task.config_file:
            args += ("--config-file", task.config_file)

        # Create temporary file that will run script/call function
        try:
            # Create
            tmpwrap = NamedTemporaryFile(
                delete=False,
                suffix=Path(task.command.script).suffix,
                prefix="wrapper_",
                mode="w",
            )
            tmpwrap_path = Path(tmpwrap.name)

            # Write
            wrapper_src = run_script_function(
                script=modified_script,
                function=task.command.function,
                args=args,
                run=False,
            )
            tmpwrap.write(wrapper_src)
            tmpwrap.flush()
            tmpwrap.close()
            os.chmod(tmpwrap_path, os.stat(tmpwrap_path).st_mode | 0o700)
        except Exception:
            safe_unlink(tmpwrap_path)
            raise

        # Get executable to run file. Also, use unbuffered output
        if task.command.kind == CommandKind.PYTHON:
            sudo_prefix = ["sudo", "-E"] if task.privileged else []
            exe_cmd = [*sudo_prefix, task.command.kind.exe, "-u"]
        else:  # Bash
            exe_cmd = ["stdbuf", "-oL", "-eL", task.command.kind.exe]

        # Combine files and args into a runnable command
        proc_cmd = [*exe_cmd, tmpwrap.name]
        self.logger.debug(
            f"Running task '{task.name}' with command:\n"
            f"'{' '.join(proc_cmd)}'"
        )

        # Logging
        log_file = self.logger.generate_logfile_path(task_id)
        self.logger.set_total(task_id, n_steps + 1)  # +1 for finishing step
        self.logger.info(
            f"\\[{task.name}] Logging to {log_file}", syntax_highlight=False
        )
        flog = log_file.open("w", encoding="utf-8", errors="replace")

        # Run and stream
        try:
            success = self._spawn_and_stream(proc_cmd, flog, task_id)
        except Exception:
            success = TaskTerminationType.FAILURE
        finally:
            safe_unlink(modified_script)
            safe_unlink(tmpwrap_path)
            flog.close()
            return success

    def _worker(self, task: ResolvedTask) -> None:
        """
        Run a task in a worker thread.

        :param task: The task to run
        :type task: ResolvedTask
        """
        task_id = self.logger.add_task(task.name, total=1)
        try:
            success = self.run_task(task, task_id)
        except Exception:
            success = TaskTerminationType.FAILURE
        finally:
            self.logger.finish_task(task_id, success)
            self.logger.debug(
                f"Task '{task.name}' completed {'sucessfully' if success == TaskTerminationType.SUCCESS else 'with errors'}"
            )
            with self.lock:
                self.results[task] = success
                self.queue.put(task)

    def run(self) -> None:
        """Run all scheduled tasks, respecting dependencies."""
        running = {}
        while True:
            with self.lock:
                for task in self.tasks:
                    # Skip already running or completed tasks
                    if task in self.results or task in self.scheduled:
                        continue

                    results_to_name = {
                        t.name: res for t, res in self.results.items()
                    }

                    # Skip tasks whose dependencies have failed
                    if any(
                        results_to_name.get(dep, None)
                        in {
                            TaskTerminationType.FAILURE,
                            TaskTerminationType.SKIPPED,
                        }
                        for dep in task.depends_on
                    ):
                        self.results[task] = TaskTerminationType.SKIPPED
                        self.logger.warning(
                            f"Skipping task '{task.name}' because a dependency failed or was skipped"
                        )

                        task_id = self.logger.add_task(task.name, total=1)
                        self.logger.finish_task(
                            task_id, TaskTerminationType.SKIPPED
                        )
                        continue

                    # Start tasks whose dependencies are all met
                    if all(
                        results_to_name.get(dep, None)
                        in {
                            TaskTerminationType.SUCCESS,
                            TaskTerminationType.PARTIAL,
                        }
                        for dep in task.depends_on
                    ):
                        t = Thread(target=self._worker, args=(task,))
                        t.start()
                        running[task] = t
                        self.scheduled.add(task)

            if not running:
                break

            finished = self.queue.get()
            running[finished].join()
            del running[finished]
