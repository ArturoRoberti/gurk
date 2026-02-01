import subprocess
import sys
from pathlib import Path
from typing import IO

import commentjson
import pytest

from gurk.lib.core import core
from gurk.lib.logger import (
    ActiveLogger,
    Logger,
    LoggerSeverity,
    allow_missing_logger,
)
from gurk.lib.utils.common import IS_GITHUB_RUNNER
from gurk.lib.utils.configs import load_yaml
from gurk.lib.utils.plugins import (
    GurkArgumentParser,
    get_combined_plugin_tasks,
)
from gurk.lib.utils.scripts import check_script_blocks


def test_task(task: str) -> None:
    """Parametrized test for any task. Used mainly in github actions to test affected tasks only."""

    # Get task info
    with allow_missing_logger():
        task_info = get_combined_plugin_tasks()
    if task not in task_info:
        pytest.fail(f"Task '{task}' not found in available tasks")

    # Check script
    script_errors = check_script_blocks(task_info[task]["script"])
    if script_errors:
        errors_str = "ERROR: " + "\nERROR: ".join(script_errors)
        pytest.fail(
            f"Task '{task}' script contains disallowed top-level blocks: {errors_str}"
        )

    # Check config file
    config_file = task_info[task]["config_file"]
    if config_file:
        if not config_file.is_file():
            pytest.fail(
                f"Config file '{config_file}' for task '{task}' does not exist"
            )
        elif str(config_file).endswith((".json", ".jsonc")):
            try:
                with config_file.open("r") as f:
                    commentjson.load(f)
            except Exception as ex:
                pytest.fail(
                    f"Failed to load JSON config file '{config_file}' for task '{task}': {ex}"
                )
        elif str(config_file).endswith((".yml", ".yaml")):
            try:
                load_yaml(config_file)
            except Exception as ex:
                pytest.fail(
                    f"Failed to load YAML config file '{config_file}' for task '{task}': {ex}"
                )
        elif str(config_file).endswith(".bash"):
            # Basic syntax check for bash scripts
            result = subprocess.run(
                ["bash", "-n", str(config_file)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                pytest.fail(
                    f"Syntax error in bash config file '{config_file}' for task '{task}': {result.stderr}"
                )

    # Run task and capture task results
    if IS_GITHUB_RUNNER:
        # For now, only run in GitHub Actions runner to avoid askpass prompts
        captured = []
        logger = Logger(True, True)
        with ActiveLogger(logger):
            with pytest.raises(SystemExit) as e:
                core.main(
                    option={task: {"enabled": True}},
                    cli_args=["--force"],
                    parser_base=GurkArgumentParser(
                        add_verbose_arg=False,
                        add_non_interactive_arg=False,
                        add_force_arg=True,
                        add_task_args=False,
                        allow_complex_types=False,
                    ),
                    _captured=captured,
                )

            if e.value.code != 0:
                logger.fatal(
                    f"Core exited with non-zero code for task '{task}'"
                )

            successful_tasks = [task for task in captured if task[2]]
            failed_tasks = [task for task in captured if not task[2]]

            def print_task_outputs(
                tasks: list[tuple[str, str, bool]], file: IO[str] | None = None
            ) -> None:
                """
                Print the contents of task output files.

                :param tasks: List of tuples containing task name, output file path, and success status
                :type tasks: list[tuple[str, str, bool]]
                :param file: The output file (stdout/stderr). If None, defaults to stdout.
                :type file: IO[str] | None
                """
                for task in tasks:
                    # Print task name
                    logger.richprint(f"\n{task[0]}:", file=file)
                    # Print the logfile (if it exists - would not be the case in e.g. a skipped task)
                    if task[1] is not None and Path(task[1]).is_file():
                        with open(task[1], "r") as f:
                            logger.richprint(f.read(), file=file)

            # Print successful task outputs
            if successful_tasks:
                logger.padded_print(
                    f"Successful tasks ({len(successful_tasks)})"
                )
                print_task_outputs(successful_tasks)
            else:
                logger.error("No successful tasks")

            # Print failed task outputs
            if failed_tasks:
                logger.padded_print(
                    f"Failed tasks ({len(failed_tasks)})", file=sys.stderr
                )
                print_task_outputs(failed_tasks, file=sys.stderr)
            else:
                logger.info("No failed tasks")

            if failed_tasks:
                logger.fatal("Some tasks failed during testing.")
    else:
        Logger.logrichprint(
            LoggerSeverity.WARNING,
            "Skipping task test (not in GitHub Actions runner).",
        )
