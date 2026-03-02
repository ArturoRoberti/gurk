# Copyright 2026 Arturo Roberti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import getpass
import os
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from rich.markup import escape

from gurk.lib.context import get_logger
from gurk.lib.core.plugins import GurkArgumentParser
from gurk.lib.core.processor import Processor
from gurk.lib.core.scheduler import Scheduler
from gurk.lib.shared.system_info import get_system_info
from gurk.lib.shared.tasks import CustomTaskDictCollection
from gurk.lib.utils import SETUP_DONE_FILE, typecheck


def check_askpass() -> bool:
    """
    Check that 'SUDO_ASKPASS' environment variable is set to a valid executable script.

    :return: True if 'SUDO_ASKPASS' is properly set, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check 'SUDO_ASKPASS'
    askpass = os.getenv("SUDO_ASKPASS")
    if not askpass:
        logger.debug("'SUDO_ASKPASS' environment variable is not set")
        return False
    elif not Path(askpass).is_file():
        logger.warning(f"'SUDO_ASKPASS' script '{askpass}' not found")
        return False
    elif not os.access(askpass, os.X_OK):
        logger.warning(f"'SUDO_ASKPASS' script '{askpass}' is not executable")
        return False

    return True


def get_sudo_askpass() -> Path:
    """
    Create a temporary sudo askpass script that provides the user's sudo password.

    :return: Path to the temporary askpass script
    :rtype: Path
    """
    # Get logger
    logger = get_logger()

    # Reset sudo permissions
    subprocess.run(["sudo", "-k"])

    # Create temporary askpass file
    with NamedTemporaryFile(mode="w", delete=False) as askpass_file:
        attempts = 3
        while attempts > 0:
            response = logger.ask(
                f"{escape('[gurk]')} password for {getpass.getuser()}", True
            )
            test_response = subprocess.run(
                ["sudo", "-S", "-v"],
                input=response + "\n",
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if test_response.returncode == 0:
                break
            else:
                if attempts != 1:
                    print("Sorry, try again.", file=sys.stderr)
                attempts -= 1
        else:
            print("gurk: 3 incorrect password attempts", file=sys.stderr)
            raise SystemExit(1)

        askpass_file.write("#!/bin/sh\n" f"echo '{response}'\n")
        askpass_path = askpass_file.name

    os.chmod(askpass_path, 0o700)
    return askpass_path


def prompt_setup() -> None:
    """
    Prompt the user to run setup if it has never been run before.
    """
    # Get logger
    logger = get_logger()

    if not SETUP_DONE_FILE.is_file():
        print(
            "It seems that this is the first time you are running gurk. "
            "It is recommended to run the setup first to ensure all "
            "possible manual steps are taken care of."
        )
        if logger.prompt_bool(
            "Would you like to run the setup now?",
        ):
            from gurk.cli.setup import main as setup_main

            setup_main([], "", "")

        # Mark setup as done
        SETUP_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETUP_DONE_FILE.touch()


@typecheck
def main(
    option: CustomTaskDictCollection,
    cli_args: list[str],
    parser_base: GurkArgumentParser,
    askpass: str | None = None,
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
    :param askpass: (Internal) Sudo askpass path for testing purposes
    :type askpass: str | None
    :param _captured: (Internal) Captured output for testing purposes
    :type _captured: list[str] | None
    :raises Exception: Propagates any exception raised during processing
    """
    # Get logger
    logger = get_logger()

    # Prompt to run the 'setup' command upon first usage
    if not logger.non_interactive:
        prompt_setup()

    # Check system information
    system_info = get_system_info()  # Raises exception if incompatible system
    logger.debug(f"System information: {system_info}")

    # Load option and process tasks
    processor = Processor(option, cli_args, parser_base)

    # Check if a prompt is needed to get sudo access
    if not (askpass or check_askpass() or "pytest" in sys.modules):
        if logger.non_interactive:
            logger.fatal(
                "sudo access is required to run tasks. Please set the "
                "'SUDO_ASKPASS' environment variable or run in interactive mode."
            )
        askpass_prompted = True
    else:
        askpass_prompted = False

    try:
        # Get sudo password
        askpass_path = None  # Set default value in case of early exception
        if askpass_prompted:
            # Prompt for sudo password
            askpass_path = get_sudo_askpass()
        else:
            # Get existing askpass path
            askpass_path = askpass or os.getenv("SUDO_ASKPASS")

        # Schedule and run tasks (where possible, in parallel)
        scheduler = Scheduler(processor.tasks, askpass_path)
        scheduler.run()

        # Save failed tasks (pytest usage)
        if _captured is not None:
            _captured.extend(scheduler.get_results())

    except Exception as e:
        raise e

    finally:
        # Remove temporary sudo askpass file, if it was created via gurk
        if (
            askpass_prompted
            and askpass_path is not None
            and Path(askpass_path).is_file()
        ):
            os.remove(askpass_path)
