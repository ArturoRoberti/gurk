import os
import shutil
import sys
import traceback
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path

from gurk.lib.core.scheduler import Scheduler
from gurk.lib.core.task_processor import TaskProcessor
from gurk.lib.logger import Logger, LoggerSeverity
from gurk.lib.utils.cli import CoreCliProcessor, get_sudo_askpass, prompt_setup


def main(argv, prog, description, _captured=None):
    parser = ArgumentParser(
        prog=prog,
        description=description,
        formatter_class=lambda prog: ArgumentDefaultsHelpFormatter(
            prog=prog,
            max_help_position=60,
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "-y",
        "--yes",
        "--non-interactive",
        dest="non_interactive",
        action="store_true",
        help="IAutomatically answer 'yes' to or ignore all prompts",
    )
    args, remaining = parser.parse_known_args(argv)

    # Handle unknown options masquerading as tasks
    invalid = [t for t in remaining if t.startswith("-")]
    if invalid:
        parser.error(f"unrecognized arguments: {' '.join(invalid)}")

    # Get 'NON_INTERACTIVE' from env if not specified
    if not args.non_interactive:
        args.non_interactive = os.getenv(
            "NON_INTERACTIVE", "false"
        ).lower() in ("true", "yes", "1")

    # Set default values in case of early exception
    logger, cloned_config_dir, askpass_path = None, None, None

    try:
        # Request sudo access at the start
        askpass_path = get_sudo_askpass()

        # Prompt to run the 'setup' command upon first usage
        prompt_setup(args.yes)

        with Logger(args.verbose) as logger:
            # TODO: Fix 'tasks' and 'cmd' not defined
            tasks = None
            cmd = None
            setup_processor = CoreCliProcessor(logger, args, argv, tasks, cmd)

            # Process args
            processed_args, cloned_config_dir = setup_processor.process_args()

            # Check system information
            setup_processor.check_system_compatibility()

            # Load config file and process tasks
            task_processor = TaskProcessor(logger, processed_args)

            # Preparation
            if not processed_args.disable_preparation:
                setup_processor.prepare()

            # Schedule and run tasks (where possible, in parallel)
            scheduler = Scheduler(
                logger, task_processor.resolved_tasks, askpass_path
            )
            scheduler.run()

            # Save failed tasks (pytest usage)
            if _captured is not None:
                _captured.extend(scheduler.get_results())

        # Final message
        logger.done(
            "All tasks completed - You may need to "
            "reboot for some changes to take effect"
        )

    except (KeyboardInterrupt, Exception) as e:
        traceback_str = traceback.format_exc()
        traceback_msg = (
            f"An Exception occured: {e.__class__.__name__} - {e}\n\n{traceback_str}"
            if str(e).strip()
            else ""
        )
        interrupt_msg = (
            "Process interrupted by user"
            if isinstance(e, KeyboardInterrupt)
            else traceback_msg
        )
        if logger is not None:
            logger.fatal(interrupt_msg)
        else:
            Logger.logrichprint(LoggerSeverity.FATAL, interrupt_msg)
            sys.exit(1)
    finally:
        # Remove temporary sudo askpass file
        if askpass_path is not None and Path(askpass_path).is_file():
            os.remove(askpass_path)
        # Remove cloned config directory if applicable
        if cloned_config_dir is not None and cloned_config_dir.is_dir():
            shutil.rmtree(cloned_config_dir)
