import errno
import json
import os
import pty
import shlex
import subprocess
import termios
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from re import sub
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Event, Lock, Thread
from typing import Dict, List, Optional, Set, TextIO, Tuple

from cmstp.core.logger import Logger
from cmstp.utils.common import CommandKind
from cmstp.utils.interface import run_script_function
from cmstp.utils.logger import TaskTerminationType
from cmstp.utils.patterns import PatternCollection
from cmstp.utils.scripts import (
    Command,
    ScriptBlock,
    ScriptBlockTypes,
    get_block_spans,
)
from cmstp.utils.system_info import get_system_info
from cmstp.utils.tasks import ResolvedTask


@dataclass
class Scheduler:
    """Schedules and runs tasks with dependencies, handling logging and progress tracking."""

    # fmt: off
    logger:       Logger             = field(repr=False)
    tasks:        List[ResolvedTask] = field(repr=False)
    askpass_file: str                = field(repr=False)

    results:   Dict[ResolvedTask, TaskTerminationType] = field(init=False, repr=False, default_factory=dict)
    scheduled: Set[ResolvedTask]                       = field(init=False, repr=False, default_factory=set)

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
        # Create temporary file to run later
        original_path = Path(command.script)
        tmp = NamedTemporaryFile(delete=False, suffix=f"_{original_path.name}")
        tmp_path = Path(tmp.name)
        tmp.close()

        # Analyze script blocks
        script_blocks = get_block_spans(original_path)

        # Main processing loop
        n_steps = 0
        with original_path.open(
            "r", encoding="utf-8", errors="replace"
        ) as src, tmp_path.open("w", encoding="utf-8") as dst:
            for idx, line in enumerate(src):
                # Detect current block
                curr_block = [
                    block
                    for block in script_blocks
                    if block["lines"][0] <= idx <= block["lines"][1]
                ]
                if not curr_block:
                    curr_block = ScriptBlock(
                        type=ScriptBlockTypes.OTHER, name=None, lines=(0, 0)
                    )
                else:
                    curr_block = curr_block[0]

                # Look for STEP instances
                step_patterns = PatternCollection.STEP.patterns
                m_comment = step_patterns["comment"](progress=True).match(line)
                m_any = step_patterns["any"](progress=True).match(line)
                if m_comment:
                    # STEP comment is found
                    step = m_comment.group(1).strip()
                elif m_any:
                    # Assumed (unwanted, manual) STEP print statement is found
                    step = m_any.group(1).strip()
                else:
                    # Not a STEP instance, write as is
                    dst.write(line)
                    continue

                # Handle STEP replacement/removal
                indent = len(line) - len(line.lstrip())
                if (
                    (
                        command.function
                        and curr_block["type"] == ScriptBlockTypes.FUNCTION
                        and curr_block["name"] == command.function
                    )
                    or (
                        not command.function
                        and curr_block["type"] == ScriptBlockTypes.ENTRYPOINT
                    )
                ) and m_comment:
                    # Replace STEP comments with print statements
                    step_msg = f"\n__STEP__: {step}"
                    if command.kind == CommandKind.PYTHON:
                        msg = f"print({step_msg!r})"
                    else:
                        step_msg += "\n"
                        msg = f"printf %s {shlex.quote(step_msg)}"

                    # Write replaced STEP print statement
                    dst.write(f"{' ' * indent}{msg}\n")

                    # Add to step count
                    n_steps += 1
                else:
                    # Write removed (assumed) STEP print statement
                    dst.write(
                        f"{' ' * indent}{'pass' if command.kind == CommandKind.PYTHON else ':'}\n"
                    )

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
                        # Read data and check end of file (EOF)
                        try:
                            raw_data = os.read(master_file.fileno(), 4096)
                        except OSError as e:
                            if e.errno == errno.EIO:
                                # EOF shows up as EIO (Input/Output error)
                                self.logger.debug(
                                    "(This is normal) PTY reader encountered "
                                    "an EIO error - treating as EOF."
                                )
                                break
                            else:
                                raise e

                        # Read and normalize data
                        data = raw_data.decode(
                            encoding="utf-8", errors="replace"
                        )
                        data = sub(r"\r+\n|\r{2,}", "\n", data)
                        data = data.replace("\r", "")

                        for line_raw in data.splitlines():
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
            if not wrapper_dir.is_dir():
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
            self.logger.debug("Task failed with non-zero exit code.")
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
            f"Running task '{task.name}' with command:"
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
            self.logger.debug(
                f"Task '{task.name}' failed, as an exception occurred during '_spawn_and_stream'."
            )
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
            self.logger.debug(
                f"Task '{task.name}' failed, as an exception occurred during 'run_task'."
            )
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

    def get_results(self) -> List[Tuple[str, str, bool]]:
        """
        Get a list of all tasks with their results.

        :return: List of tasks in the format [task_name, task_logfile, successful]
        :rtype: List[Tuple[str, str, bool]]
        """
        all_tasks = []
        for task, result in self.results.items():
            for _, task_info in self.logger.task_infos.items():
                if task_info["name"] == task.name:
                    all_tasks.append(
                        (
                            task.name,
                            str(task_info["logfile"]),
                            result == TaskTerminationType.SUCCESS,
                        )
                    )
        return all_tasks
