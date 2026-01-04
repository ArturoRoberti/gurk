import subprocess
from typing import List, TypedDict

import commentjson

from gurk.core.logger import Logger, LoggerSeverity
from gurk.scripts.python.helpers._interface import get_config_args
from gurk.scripts.python.helpers.common import add_alias
from gurk.scripts.python.helpers.processing import (
    InstallCommands,
    get_clean_lines,
    install_packages_from_list,
    install_packages_from_txt_file,
)
from gurk.utils.interface import bash_check


def install_apt_packages(*args: List[str]) -> None:
    """
    Install packages using apt package manager.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of apt packages, as no task config file is provided",
            warning=True,
        )
        return

    # (STEP) Installing apt packages
    install_packages_from_txt_file(InstallCommands.APT, config_file)


def install_snap_packages(*args: List[str]) -> None:
    """
    Install packages using snap package manager.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of snap packages, as no task config file is provided",
            warning=True,
        )
        return

    # (STEP) Installing Requirement(s)
    install_packages_from_list(InstallCommands.APT, ["snapd"])
    # TODO: Ensure snapd service is running

    # (STEP) Installing snap packages
    install_packages_from_txt_file(InstallCommands.SNAP, config_file)


def install_flatpak_packages(*args: List[str]) -> None:
    """
    Install packages using flatpak package manager.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, remaining_args = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of flatpak packages, as no task config file is provided",
            warning=True,
        )
        return

    # (STEP) Installing Requirement(s)
    install_packages_from_list(InstallCommands.APT, ["flatpak"])

    # (STEP) Configuring flathub remote - Ignore errors if remote does not exist
    subprocess.run(
        ["sudo", "flatpak", "remote-delete", "flathub"], capture_output=True
    )
    subprocess.run(
        [
            "sudo",
            "flatpak",
            "remote-add",
            "flathub",
            "https://flathub.org/repo/flathub.flatpakrepo",
        ],
        capture_output=True,
    )

    # (STEP) Installing flatpak packages
    install_packages_from_txt_file(InstallCommands.FLATPAK, config_file)

    # Add aliases for flatpak packages
    if "--create-aliases" in remaining_args:
        Logger.step("Adding aliases for flatpak packages...")
        for pkg in get_clean_lines(config_file):
            # Use probable package name for alias
            pkg_name = pkg.split(".")[-1]
            add_alias(f"{pkg_name}='(flatpak run {pkg} > /dev/null &)'")


def install_npm_packages(*args: List[str]) -> None:
    """
    Install packages using npm package manager.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of npm packages, as no task config file is provided",
            warning=True,
        )
        return

    # (STEP) Installing Requirement(s)
    install_packages_from_list(InstallCommands.APT, ["npm", "nodejs"])

    # (STEP) Installing npm packages
    install_packages_from_txt_file(InstallCommands.NPM, config_file)


def install_pipx_packages(*args: List[str]) -> None:
    """
    Install packages using pipx package manager.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of pipx packages, as no task config file is provided",
            warning=True,
        )
        return

    # (STEP) Installing pipx packages
    install_packages_from_txt_file(InstallCommands.PIPX, config_file)


def install_vscode_extensions(*args: List[str]) -> None:
    """
    Install VSCode extensions.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of VSCode extensions, as no task config file is provided",
            warning=True,
        )
        return

    # Check VSCode is installed
    result = bash_check("check_install_vscode")
    if not result.returncode == 0:
        Logger.logrichprint(
            LoggerSeverity.FATAL,
            "VSCode is not installed. Please install VSCode before installing extensions.",
        )
        raise EnvironmentError

    # Install extensions
    install_packages_from_txt_file(InstallCommands.VSC_EXT, config_file)


def install_docker_images(*args: List[str]) -> None:
    """
    Pull docker images from Docker Hub.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping pulling of docker images, as no task config file is provided",
            warning=True,
        )
        return

    # Check docker is installed
    result = bash_check("check_install_docker")
    if not result.returncode == 0:
        Logger.logrichprint(
            LoggerSeverity.FATAL,
            "Docker is not installed. Please install Docker before pulling images.",
        )
        raise EnvironmentError(result.stderr)

    # Typing helper classes
    class DockerImageInfo(TypedDict):
        # fmt: off
        registry: str
        image:    str
        tag:      str
        # fmt: on

    # Load docker images - also expand environment variables
    docker_images_info: List[DockerImageInfo] = commentjson.load(
        config_file.open("r", encoding="utf-8")
    )
    docker_images = [
        f"{item.get('registry', 'docker.io')}/{item['image']}:{item.get('tag', 'latest')}"
        for item in docker_images_info
    ]
    if not docker_images:
        Logger.step(
            "No docker images found in the provided config file. Skipping pulling of docker images.",
        )
        return

    # (STEP) Pulling docker images
    install_packages_from_list(InstallCommands.DOCKER, docker_images)
