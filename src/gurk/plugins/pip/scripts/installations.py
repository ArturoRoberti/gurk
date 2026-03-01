import shutil
import subprocess
import venv
from pathlib import Path

import commentjson

from gurk import (
    InstallCommandsBase,
    LoggerSeverity,
    install_packages_from_txt_file,
    log_step,
    logrichprint,
    parse_task_args,
)


class PipInstallCommands(InstallCommandsBase):
    # fmt: off
    PIP  = "python3 -m pip install --user"
    PIPX = "python3 -m pipx install"
    # fmt: on


def install_pipx_packages(*args: list[str]) -> None:
    """
    Install packages using pipx package manager.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # (STEP) Installing pipx packages
    install_packages_from_txt_file(
        PipInstallCommands.PIPX, task_args.config_file
    )


def install_pip_environments(*args: list[str]) -> None:
    """
    Install packages into python environments using pip.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # Get pip environments info
    pip_envs: dict[str, list[str]] = commentjson.load(
        task_args.config_file.open("r", encoding="utf-8")
    )
    if not pip_envs:
        log_step(
            "Skipping installation of pip packages, as no environments are specified",
        )
        return

    # (STEP) Creating virtual environments in {Path.home() / '.virtualenvs'}
    base_venv_dir = Path.home() / ".virtualenvs"
    for venv_name, packages in pip_envs.items():
        if not packages:
            log_step(
                f"Skipping installation of pip packages for environment '{venv_name}', as no packages are specified",
                warning=True,
            )
            continue

        # Handle existing virtual environment
        venv_dir = base_venv_dir / venv_name
        if venv_dir.exists():
            if not task_args.force:
                log_step(
                    f"Skipping creation of environment '{venv_name}', as it already exists",
                    warning=True,
                )
                continue
            else:
                logrichprint(
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
            log_step(
                f"Failed to install packages for environment '{venv_name}'",
                warning=True,
            )
        else:
            log_step(
                f"Successfully installed packages for environment '{venv_name}'"
            )
