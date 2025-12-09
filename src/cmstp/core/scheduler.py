import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from tempfile import NamedTemporaryFile
from threading import Lock, Thread
from typing import Dict, List, Optional, Set, TextIO, Tuple

from cmstp.core.logger import Logger
from cmstp.utils.command import Command, CommandKind
from cmstp.utils.interface import run_script_function
from cmstp.utils.patterns import PatternCollection
from cmstp.utils.system_info import get_system_info
from cmstp.utils.tasks import ResolvedTask


@dataclass
class Scheduler:
    """Schedules and runs tasks with dependencies, handling logging and progress tracking."""

    # fmt: off
    logger:      Logger             = field(repr=False)
    tasks:       List[ResolvedTask] = field(repr=False)

    results:   Dict[ResolvedTask, bool] = field(init=False, repr=False, default_factory=dict)
    scheduled: Set[ResolvedTask]        = field(init=False, repr=False, default_factory=set)

    lock:      Lock  = field(init=False, repr=False, default_factory=Lock)
    queue:     Queue = field(init=False, repr=False, default_factory=Queue)
    # fmt: on

    @staticmethod
    def _prepare_script(command: Command) -> Tuple[Path, int]:
        """
        Prepare a copy of the desired script that
        - Uses STEP statements only if in the desired function (or entrypoint)
        - Converts all STEP and STEP_NO_PROGRESS comments into equivalent print statements.
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

        def detect_block_start(stripped: str, indent_len: int):
            """Return (kind, name, location_indent) or None."""
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

        def block_end_reached(stripped: str, indent_len: int):
            """Return True if the current line ends the current block."""
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

            Args:
                line (str): The line to check.
            Returns:
                Tuple[Optional[str], Optional[str]]: (step message, step type)
                    step type is
                    - "comment*" for STEP comments,
                    - "output*" for STEP print statements
                    - None if not a STEP line.
            """
            step_patterns = PatternCollection.STEP.patterns

            # See if it's a STEP comment
            m_comment_progress = step_patterns["comment"](progress=True).match(
                line
            )
            if m_comment_progress:
                return m_comment_progress.group(1).strip(), "comment_progress"

            m_comment_no_progress = step_patterns["comment"](
                progress=False
            ).match(line)
            if m_comment_no_progress:
                return (
                    m_comment_no_progress.group(1).strip(),
                    "comment_no_progress",
                )

            # See if it's a STEP print statement - ASSUME any line containing __STEP__ resp. __STEP_NO_PROGRESS__ is a STEP print statement
            m_any_progress = step_patterns["any"](progress=True).match(line)
            if m_any_progress:
                return m_any_progress.group(1).strip(), "any_progress"

            m_any_no_progress = step_patterns["any"](progress=False).match(
                line
            )
            if m_any_no_progress:
                return m_any_no_progress.group(1).strip(), "any_no_progress"

            return None, None

        def replace_potential_step(
            line: str, indent: str, in_desired: bool
        ) -> str:
            """
            Replace a STEP comment with print statements, preserving indentation.
            If not in_desired, remove the STEP comment.
            """
            step, step_type = get_step(line)
            if step is not None:
                if step_type == "comment_no_progress" or (
                    in_desired and step_type == "comment_progress"
                ):
                    # TODO: make safe, i.e. replace any " with ' (or similar)
                    # Replace STEP/STEP_NO_PROGRESS comments with print statements
                    if step_type == "comment_no_progress":
                        step_msg = f"\\n__STEP_NO_PROGRESS__: {step}"
                    else:
                        step_msg = f"\\n__STEP__: {step}"

                    if command.kind == CommandKind.PYTHON:
                        msg = f'print(f"{step_msg}")'
                    else:
                        msg = f'printf "{step_msg}\\n"'

                    return f"{indent}{msg}\n"

                elif not in_desired and step_type in (
                    "comment_progress",
                    "any_progress",
                ):
                    # Remove STEP print statements
                    return f"{indent}{'pass' if command.kind == CommandKind.PYTHON else ':'}\n"

                # else: Leave STEP_NO_PROGRESS print statements

            return line

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
                if step and step_type == "any_progress":
                    n_steps += 1

        return tmp_path, n_steps

    def _spawn_and_stream(
        self, proc_cmd: List[str], flog: TextIO, task_id: int
    ):
        """Spawn a subprocess and stream its output to the logfile and progress tracker."""

        def reader(pipe: TextIO, is_stdout: bool):
            try:
                for raw in iter(pipe.readline, ""):
                    if raw == "":
                        break
                    line = raw.rstrip("\n")
                    flog.write(line + "\n")
                    flog.flush()
                    if is_stdout:
                        m_progress = PatternCollection.STEP.patterns["output"](
                            progress=True
                        ).match(line)
                        if m_progress:
                            self.logger.update_task(
                                task_id, m_progress.group(1).strip()
                            )

                        m_no_progress = PatternCollection.STEP.patterns[
                            "output"
                        ](progress=False).match(line)
                        if m_no_progress:
                            self.logger.update_task(
                                task_id,
                                m_no_progress.group(1).strip(),
                                advance=False,
                            )
            finally:
                try:
                    pipe.close()
                except Exception:
                    pass

        process = subprocess.Popen(
            proc_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        t_out = Thread(target=reader, args=(process.stdout, True), daemon=True)
        t_err = Thread(
            target=reader, args=(process.stderr, False), daemon=True
        )
        t_out.start()
        t_err.start()
        exit_code = process.wait()
        t_out.join()
        t_err.join()
        return exit_code == 0

    def run_task(
        self,
        task: ResolvedTask,
        task_id: int,
    ) -> bool:
        """Run a single task, logging its output and tracking progress."""
        # Prepare script with modified step statements
        modified_script, n_steps = self._prepare_script(task.command)
        self.logger.debug(
            f"Prepared modified script for task '{task.name}' at {modified_script} with {n_steps} steps"
        )

        def safe_unlink(path: Optional[Path]):
            """
            Unlink files that may or may not have been unlinked yet
            """
            if path and isinstance(path, Path) and path.exists():
                try:
                    path.unlink()
                except Exception:
                    # Already unlinked
                    pass

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
                modified_script, function=task.command.function, run=False
            )
            tmpwrap.write(wrapper_src)
            tmpwrap.flush()
            tmpwrap.close()
            os.chmod(tmpwrap_path, os.stat(tmpwrap_path).st_mode | 0o700)
        except Exception:
            safe_unlink(tmpwrap_path)
            raise

        # Add system info as an arg
        args = task.args + ("--system-info", json.dumps(get_system_info()))
        if task.config_file:
            args += ("--config-file", task.config_file)

        # Get executable to run file. Also, use unbuffered output
        if task.command.kind == CommandKind.PYTHON:
            exe_cmd = [task.command.kind.exe, "-u"]
        else:  # Bash
            exe_cmd = ["stdbuf", "-oL", "-eL", task.command.kind.exe]

        # Combine files and args into a runnable command
        proc_cmd = [*exe_cmd, tmpwrap.name, *args]
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
            success = False
        finally:
            safe_unlink(modified_script)
            safe_unlink(tmpwrap_path)
            flog.close()
            return success

    def _worker(self, task: ResolvedTask):
        """Worker thread to run a task."""
        task_id = self.logger.add_task(task.name, total=1)
        success = False
        try:
            success = self.run_task(task, task_id)
        except Exception:
            success = False
        finally:
            self.logger.finish_task(task_id, success)
            self.logger.debug(
                f"Task '{task.name}' completed {'sucessfully' if success else 'with errors'}"
            )
            with self.lock:
                self.results[task] = success
                self.queue.put(task)

    def run(self):
        """Run all scheduled tasks, respecting dependencies."""
        running = {}
        while True:
            with self.lock:
                for task in self.tasks:
                    if task in self.results or task in self.scheduled:
                        continue

                    results_to_name = {
                        t.name: res for t, res in self.results.items()
                    }
                    if all(
                        results_to_name.get(dep, False)
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
