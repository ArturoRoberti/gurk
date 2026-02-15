import getpass
import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

from gurk.lib.core.context import get_logger
from gurk.lib.utils.common import SETUP_DONE_FILE


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
        logger.warning("'SUDO_ASKPASS' environment variable is not set")
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
                f"\\[gurk] password for {getpass.getuser()}", True
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
                    print("Sorry, try again.")
                attempts -= 1
        else:
            print("gurk: 3 incorrect password attempts")
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
