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

import subprocess
from enum import Enum
from pathlib import Path

from gurk.lib.utils import typecheck

from .interface import log_step


class InstallCommandsBase(Enum):
    """
    Predefined installation commands for various package managers.
    """

    @staticmethod
    @typecheck
    def _flock_command(cmd: str) -> str:
        """
        Wraps a command with flock to prevent concurrent executions.

        :param cmd: The command to wrap
        :type cmd: str
        :return: The wrapped command
        :rtype: str
        """
        return f"sudo flock /var/lib/dpkg/lock-frontend {cmd}"

    @property
    def command(self) -> str:
        """Get the installation command string."""
        return self.value


class BuiltinInstallCommands(InstallCommandsBase):
    """
    Predefined installation commands for various package managers.
    """

    # fmt: off
    APT     = InstallCommandsBase._flock_command("apt-get install -y")
    DPKG    = InstallCommandsBase._flock_command("dpkg -i")
    SNAP    = "sudo snap install"
    FLATPAK = "sudo flatpak install -y"
    NPM     = "sudo npm install -g"
    # fmt: on


@typecheck
def get_clean_lines(filename: Path) -> list[str]:
    """
    Reads a file and returns a list of lines with comments and extra whitespace removed.
    Lines starting with '#' or empty after stripping are ignored.

    :param filename: Path to the input file
    :type filename: Path
    :return: List of cleaned lines
    :rtype: list[str]
    """
    clean_lines = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            # Remove inline comments and strip whitespace
            line = line.split("#", 1)[0].strip()
            # Skip empty lines
            if line:
                clean_lines.append(line)
    return clean_lines


@typecheck
def install_packages_from_list(
    install_command: InstallCommandsBase, packages: list[str]
) -> None:
    """
    Installs a list of packages using the specified package manager command.

    :param install_command: InstallCommandsBase enum value specifying the installation command
    :type install_command: InstallCommandsBase
    :param packages: List of package names to install
    :type packages: list[str]
    """
    for pkg in packages:
        cmd = f"{install_command.command} {pkg}"
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            log_step(f"Failed to install package: {pkg}", warning=True)
        else:
            log_step(f"Successfully installed package: {pkg}")


@typecheck
def install_packages_from_txt_file(
    install_command: InstallCommandsBase, package_file: Path
) -> None:
    """
    Installs packages listed in the given requirements file using the specified package manager command.

    :param install_command: InstallCommandsBase enum value specifying the installation command
    :type install_command: InstallCommandsBase
    :param package_file: Path to the requirements file
    :type package_file: Path
    """
    install_packages_from_list(install_command, get_clean_lines(package_file))
