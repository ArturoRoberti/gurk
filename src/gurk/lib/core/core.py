import os
import shutil
from pathlib import Path

from gurk.lib.core.processor import Processor
from gurk.lib.core.scheduler import Scheduler
from gurk.lib.logger import get_logger
from gurk.lib.utils.cli import get_sudo_askpass, prompt_setup
from gurk.lib.utils.common import IS_GITHUB_RUNNER, generate_random_path
from gurk.lib.utils.plugins import GurkArgumentParser
from gurk.lib.utils.system_info import get_system_info
from gurk.lib.utils.tasks import CustomTaskDictCollection


def main(
    option: CustomTaskDictCollection,
    cli_args: list[str],
    parser_base: GurkArgumentParser,
    _captured: list[str] | None = None,
):
    """
    Main entry point for the 'run' command.

    :param option: Run option of the requested gurk plugin
    :type option: CustomTaskDictCollection
    :param cli_args: Command-line arguments to be passed to the resp. tasks
    :type cli_args: list[str]
    :param parser_base: Base argument parser, on which each task parser is built
    :type parser_base: GurkArgumentParser
    :param _captured: (Internal) Captured output for testing purposes
    :type _captured: list[str] | None
    :raises Exception: Propagates any exception raised during processing
    """
    # Get logger
    logger = get_logger()

    # Set default values in case of early exception
    cloned_config_dir, askpass_path = None, None

    try:
        # Prompt to run the 'setup' command upon first usage
        if not logger.non_interactive or IS_GITHUB_RUNNER:
            prompt_setup()

        # Check system information
        try:
            system_info = get_system_info()
            logger.debug(f"System information: {system_info}")
        except RuntimeError as e:
            logger.fatal(str(e))

        # Load option and process tasks
        processor = Processor(option, cli_args, parser_base)

        # Prompt for sudo password
        if not IS_GITHUB_RUNNER:
            non_interactive = logger.non_interactive

            if non_interactive:
                logger.warning(
                    "sudo access is required to run tasks. "
                    "Non-interactive mode is not supported for this yet."
                )

                # TEMPORARY: enable logger interactive mode to get password
                logger.non_interactive = False

            askpass_path = get_sudo_askpass()

            # TEMPORARY: restore non-interactive mode
            if non_interactive:
                logger.non_interactive = True
        else:
            # In GitHub Actions, sudo is available without a
            #   password, thus a mock askpass script suffices
            askpass_path = generate_random_path(suffix=".sh")

        # Schedule and run tasks (where possible, in parallel)
        scheduler = Scheduler(processor.tasks, askpass_path)
        scheduler.run()

        # Save failed tasks (pytest usage)
        if _captured is not None:
            _captured.extend(scheduler.get_results())
    except Exception as e:
        raise e
    finally:
        # Remove temporary sudo askpass file
        if askpass_path is not None and Path(askpass_path).is_file():
            os.remove(askpass_path)
        # Remove cloned config directory if applicable
        if cloned_config_dir is not None and cloned_config_dir.is_dir():
            shutil.rmtree(cloned_config_dir)
