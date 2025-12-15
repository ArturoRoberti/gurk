import shutil
import subprocess
import sys
import traceback
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path

from cmstp.core.logger import Logger, LoggerSeverity
from cmstp.core.scheduler import Scheduler
from cmstp.core.task_processor import TaskProcessor
from cmstp.utils.cli import MainSetupProcessor
from cmstp.utils.common import PACKAGE_CONFIG_PATH


def main(argv, prog):
    parser = ArgumentParser(
        prog=prog,
        description=(
            "Main setup utility - Set up your computer based on a provided "
            "configuration (or defaults)"
        ),
        formatter_class=lambda prog: ArgumentDefaultsHelpFormatter(
            prog=prog,
            max_help_position=60,
        ),
    )
    parser.add_argument(
        "-f",
        "--config-file",
        type=Path,
        default=PACKAGE_CONFIG_PATH / "enabled.yaml",
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
    # Add '--enable-all' and '--enable-dependencies'
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
    args = parser.parse_args(argv)

    # Set default values in case of early exception
    logger, cloned_config_dir = None, None

    try:
        # Request sudo access at the start
        subprocess.run(["sudo", "-v"], check=True)

        with Logger(args.verbose) as logger:
            # Process args
            setup_processor = MainSetupProcessor(logger, args, argv)
            processed_args, cloned_config_dir = setup_processor.process_args()

            # Check system information
            setup_processor.check_system_compatibility()

            # Load config file and process tasks
            task_processor = TaskProcessor(
                logger,
                processed_args.config_file,
                processed_args.config_directory,
                processed_args.tasks,
                processed_args.enable_all,
                processed_args.enable_dependencies,
            )

            # Pre-setup
            if not processed_args.disable_preparation:
                setup_processor.prepare()

            # Schedule and run tasks (where possible, in parallel)
            scheduler = Scheduler(logger, task_processor.resolved_tasks)
            scheduler.run()

        # Final message
        logger.done(
            "All tasks completed - You may need to reboot for some changes to take effect",
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
        # Remove cloned config directory if applicable
        if cloned_config_dir is not None and cloned_config_dir.exists():
            shutil.rmtree(cloned_config_dir)
