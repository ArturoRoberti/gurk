import subprocess
from enum import Enum
from pathlib import Path
from typing import List

from cmstp.core.logger import Logger


class InstallCommands(Enum):
    # fmt: off
    APT     = "sudo flock /var/lib/dpkg/lock-frontend apt-get install -y"
    SNAP    = "sudo snap install"
    FLATPAK = "sudo flatpak install"
    NPM     = "sudo npm install -g"
    PIP     = "python3 -m pip install --user"
    PIPX    = "python3 -m pipx install"
    VSC_EXT = "code --install-extension"
    DOCKER  = "docker pull"
    # fmt: on


def get_clean_lines(filename: Path) -> List[str]:
    """
    Reads a file and returns a list of lines with comments and extra whitespace removed.
    Lines starting with '#' or empty after stripping are ignored.
    """
    # if not filename.exists():
    #     Logger.logrichprint(LoggerSeverity.FATAL, f"Config file not found: {filename}")
    #     raise FileNotFoundError

    clean_lines = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            # Remove inline comments and strip whitespace
            line = line.split("#", 1)[0].strip()
            # Skip empty lines
            if line:
                clean_lines.append(line)
    return clean_lines


# TODO: If a single package fails, finish task with neither "success" nor "failure", but "warning" status
def install_packages_from_list(
    install_command: InstallCommands, packages: List[str]
):
    """
    Installs a list of packages using the specified package manager command.
    """
    for pkg in packages:
        cmd = f"{install_command.value} {pkg}"
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            Logger.step(f"Failed to install package: {pkg}")
        else:
            Logger.step(f"Successfully installed package: {pkg}")


def install_packages_from_txt_file(
    install_command: InstallCommands, package_file: Path
):
    """
    Installs packages listed in the given requirements file using the specified package manager command.
    """
    install_packages_from_list(install_command, get_clean_lines(package_file))
