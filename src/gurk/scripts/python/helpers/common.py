from pathlib import Path

from gurk.core.logger import Logger
from gurk.utils.interface import PACKAGE_BASH_HELPERS_PATH, run_script_function


def add_alias(command: str) -> None:
    """
    Add an alias to ~/.bashrc if it doesn't already exist.

    :param command: The alias command to add
    :type command: str
    """
    alias_cmd = f"alias {command}"
    run_script_function(
        script=PACKAGE_BASH_HELPERS_PATH,
        function="write_marked",
        args=[alias_cmd, str(Path.home() / ".bashrc")],
        run=True,
        check=False,
    )
    Logger.step(f"Sucessfully added alias: {alias_cmd}")
