from pathlib import Path

from cmstp.core.logger import Logger


# TODO: Use cmstp markers instead
def add_alias(command: str) -> None:
    """
    Add an alias to ~/.bashrc if it doesn't already exist.

    :param command: The alias command to add
    :type command: str
    """
    bashrc_path = Path.home() / ".bashrc"
    alias_cmd = f"alias {command}"
    with open(bashrc_path, "r", encoding="utf-8") as bashrc:
        if alias_cmd in bashrc.read():
            Logger.step(f"Alias already exists: {alias_cmd}")
            return

    with open(bashrc_path, "a", encoding="utf-8") as bashrc:
        bashrc.write(f"\n{alias_cmd}\n")

    Logger.step(f"Sucessfully added alias: {alias_cmd}")
