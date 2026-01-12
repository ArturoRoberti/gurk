import subprocess
import time

from gurk import (
    InstallCommands,
    Logger,
    LoggerSeverity,
    add_alias,
    get_clean_lines,
    install_packages_from_list,
    install_packages_from_txt_file,
    parse_task_args,
)


def install_apt_packages(*args: list[str]) -> None:
    """
    Install packages using apt package manager.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # (STEP) Installing apt packages
    install_packages_from_txt_file(InstallCommands.APT, task_args.config_file)


def install_flatpak_packages(*args: list[str]) -> None:
    """
    Install packages using flatpak package manager.
    """
    # Parse task args
    task_args = parse_task_args(args)

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
    install_packages_from_txt_file(
        InstallCommands.FLATPAK, task_args.config_file
    )

    # Add aliases for flatpak packages
    if task_args.gurk_flatpak_create_aliases:
        Logger.step("Adding aliases for flatpak packages...")
        for pkg in get_clean_lines(task_args.config_file):
            # Use probable package name for alias
            pkg_name = pkg.split(".")[-1]
            add_alias(f"{pkg_name}='(flatpak run {pkg} > /dev/null &)'")


def install_npm_packages(*args: list[str]) -> None:
    """
    Install packages using npm package manager.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # (STEP) Installing Requirement(s)
    install_packages_from_list(InstallCommands.APT, ["npm", "nodejs"])

    # (STEP) Installing npm packages
    install_packages_from_txt_file(InstallCommands.NPM, task_args.config_file)


def install_snap_packages(*args: list[str]) -> None:
    """
    Install packages using snap package manager.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # (STEP) Installing Requirement(s)
    install_packages_from_list(InstallCommands.APT, ["snapd"])

    # (STEP) Ensuring that snapd service is running
    def start_snapd_service(remaining_attempts: int = 3) -> None:
        # Exit if max attempts are reached
        if remaining_attempts <= 0:
            msg = "Failed to start snapd service after multiple attempts."
            Logger.logrichprint(
                LoggerSeverity.FATAL,
                msg,
            )
            raise EnvironmentError(msg)

        # Check if snapd is active
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "snapd"],
                capture_output=True,
                text=True,
                check=True,
            )
            running = result.stdout.strip() == "active"
        except subprocess.CalledProcessError:
            running = False

        if running:
            Logger.logrichprint(
                LoggerSeverity.INFO,
                "snapd service is running.",
            )
            return

        # Try to start snapd if not running
        Logger.logrichprint(
            LoggerSeverity.WARNING,
            "Attempting to start snapd service...",
        )
        try:
            subprocess.run(["sudo", "systemctl", "start", "snapd"], check=True)
            time.sleep(3)  # Wait a bit for the service to start
        except subprocess.CalledProcessError:
            Logger.logrichprint(
                LoggerSeverity.WARNING,
                "Attempt to start snapd service failed.",
            )
            start_snapd_service(remaining_attempts - 1)

    start_snapd_service()

    # (STEP) Installing snap packages
    install_packages_from_txt_file(InstallCommands.SNAP, task_args.config_file)
