import os
import shutil
import sys
import traceback
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path

from cmstp.core.logger import Logger, LoggerSeverity
from cmstp.core.scheduler import Scheduler
from cmstp.core.task_processor import TaskProcessor
from cmstp.utils.cli import CoreCliProcessor, get_sudo_askpass
from cmstp.utils.common import ENABLED_CONFIG_FILE, PACKAGE_CONFIG_PATH


def main(argv, prog, description, cmd, _captured=None):
    parser = ArgumentParser(
        prog=prog,
        description=description,
        formatter_class=lambda prog: ArgumentDefaultsHelpFormatter(
            prog=prog,
            max_help_position=60,
        ),
    )
    parser.add_argument(
        "-f",
        "--config-file",
        type=Path,
        default=ENABLED_CONFIG_FILE,
        help="Path to the main configuration file",
    )
    parser.add_argument(
        "-d",
        "--config-directory",
        type=Path,
        default=PACKAGE_CONFIG_PATH,
        help="Path to the configuration directory",
    )
    parser.add_argument(
        "-t",
        "--tasks",
        type=str,
        nargs="+",
        default=None,
        help="Specify the tasks to run (default: all enabled tasks in the config file)",
    )
    parser.add_argument(
        "--enable-all",
        action="store_true",
        help="Enable all tasks in the configuration file, unless explicitly disabled",
    )
    parser.add_argument(
        "--enable-dependencies",
        action="store_true",
        help="Enable all dependencies of the specified tasks, even if they are disabled",
    )
    parser.add_argument(
        "--disable-preparation",
        action="store_true",
        help="(Not recommended) Disable updating/upgrading apt beforehand",
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
        action="store_true",
        help="Automatically answer 'yes' to all prompts",
    )
    args = parser.parse_args(argv)

    # Set default values in case of early exception
    logger, cloned_config_dir, askpass_path = None, None, None

    try:
        # Request sudo access at the start
        askpass_path = get_sudo_askpass()

        with Logger(args.verbose) as logger:
            setup_processor = CoreCliProcessor(logger, args, argv, cmd)

            # Prompt pre-setup if this was never run before
            setup_processor.prompt_setup()

            # Process args
            processed_args, cloned_config_dir = setup_processor.process_args()

            # Check system information
            setup_processor.check_system_compatibility()

            # Load config file and process tasks
            task_processor = TaskProcessor(logger, processed_args)

            # Pre-setup
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
