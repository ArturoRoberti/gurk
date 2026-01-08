import shutil
import subprocess
import venv
from pathlib import Path

import commentjson

from gurk.core.logger import Logger, LoggerSeverity
from gurk.lib.helpers import (
    InstallCommands,
    get_config_args,
    install_packages_from_txt_file,
)


def install_pipx_packages(*args: list[str]) -> None:
    """
    Install packages using pipx package manager.

    :param args: Configuration arguments
    :type args: list[str]
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


def install_pip_environments(*args: list[str]) -> None:
    """
    Install packages into python environments using pip.

    :param args: Configuration arguments
    :type args: list[str]
    """
    # Parse config args
    _, config_file, force, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of pip packages, as no task config file is provided",
            warning=True,
        )
        return

    # Get pip environments info
    pip_envs: dict[str, list[str]] = commentjson.load(
        config_file.open("r", encoding="utf-8")
    )
    if not pip_envs:
        Logger.step(
            "Skipping installation of pip packages, as no environments are specified",
        )
        return

    # (STEP) Creating virtual environments in {Path.home() / '.virtualenvs'}
    base_venv_dir = Path.home() / ".virtualenvs"
    for venv_name, packages in pip_envs.items():
        if not packages:
            Logger.step(
                f"Skipping installation of pip packages for environment '{venv_name}', as no packages are specified",
                warning=True,
            )
            continue

        # Handle existing virtual environment
        venv_dir = base_venv_dir / venv_name
        if venv_dir.exists():
            if not force:
                Logger.step(
                    f"Skipping creation of environment '{venv_name}', as it already exists",
                    warning=True,
                )
                continue
            else:
                Logger.logrichprint(
                    LoggerSeverity.WARNING,
                    f"Removing existing '{venv_name}' environment to create a new one",
                )
                shutil.rmtree(venv_dir)

        # Create new virtual environment
        venv.create(venv_dir, with_pip=True)
        pip_executable = venv_dir / "bin" / "pip"

        # Install packages
        result = subprocess.run(
            [str(pip_executable), "install", *packages],
        )
        if result.returncode != 0:
            Logger.step(
                f"Failed to install packages for environment '{venv_name}'",
                warning=True,
            )
        else:
            Logger.step(
                f"Successfully installed packages for environment '{venv_name}'"
            )
