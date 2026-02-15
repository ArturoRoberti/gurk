import os
from pathlib import Path

from gurk.lib.core.context import get_logger
from gurk.lib.core.plugins import GurkArgumentParser
from gurk.lib.core.processor import Processor
from gurk.lib.core.scheduler import Scheduler
from gurk.lib.utils.common import typecheck
from gurk.lib.utils.runner import check_askpass, get_sudo_askpass, prompt_setup
from gurk.lib.utils.system_info import get_system_info
from gurk.lib.utils.tasks import CustomTaskDictCollection


@typecheck
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
    askpass_path = None

    try:
        # Prompt to run the 'setup' command upon first usage
        if not logger.non_interactive:
            prompt_setup()

        # Check system information
        try:
            system_info = get_system_info()
            logger.debug(f"System information: {system_info}")
        except RuntimeError as e:
            logger.fatal(str(e))

        # Load option and process tasks
        processor = Processor(option, cli_args, parser_base)

        # Get sudo password
        if not check_askpass():
            if logger.non_interactive:
                logger.fatal(
                    "sudo access is required to run tasks. Please set the "
                    "'SUDO_ASKPASS' environment variable or run in interactive mode."
                )
            # Prompt for sudo password
            askpass_path = get_sudo_askpass()
        else:
            # Get existing askpass path
            askpass_path = os.getenv("SUDO_ASKPASS")

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
