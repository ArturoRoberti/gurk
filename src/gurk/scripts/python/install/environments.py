import os
import shutil
import subprocess
import venv
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TypedDict

import commentjson
from ruamel.yaml import YAML

from gurk.core.logger import Logger, LoggerSeverity
from gurk.scripts.python.helpers._interface import get_config_args
from gurk.utils.interface import bash_check


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


def install_conda_environments(*args: list[str]) -> None:
    """
    Install packages into Conda environments (no custom env directory).

    :param args: Configuration arguments
    :type args: list[str]
    """
    # Parse config args
    _, config_file, force, remaining_args = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of conda environments, as no task config file is provided",
            warning=True,
        )
        return

    # Typing helper classes
    class CondaEnv(TypedDict):
        # fmt: off
        type:           str                   # "conda", "mamba"
        conda_packages: dict[str, list[str]]  # package-name -> [channels]
        pip_packages:   list[str]
        # fmt: on

    # Get conda environments info
    conda_envs: dict[str, CondaEnv] = commentjson.load(
        config_file.open("r", encoding="utf-8")
    )
    if not conda_envs:
        Logger.step(
            "Skipping installation of conda environments, as no environments are specified",
        )
        return

    # Check if conda types are installed
    conda_exe = {"conda": None, "mamba": None}
    for conda_type in conda_exe.keys():
        result = bash_check(f"check_install_{conda_type}")
        if result.returncode == 0:
            conda_exe[conda_type] = result.stdout.strip()

    def check_env_type(env_type: str | None) -> bool:
        """Check if conda environment type field is valid."""
        if env_type is None:
            Logger.step(
                f"No environment type specified for '{env_name}' - Skipping",
                warning=True,
            )
            return False
        elif env_type not in conda_exe.keys():
            Logger.step(
                f"Unsupported environment type '{env_type}' for '{env_name}' - Skipping",
                warning=True,
            )
            return False

        for conda_type, exe in conda_exe.items():
            if env_type == conda_type and exe is None:
                Logger.step(
                    f"'{env_type}' is not installed, cannot create environment '{env_name}' - Skipping",
                    warning=True,
                )
                return False

        return True

    # (STEP) Creating conda environments
    for env_name, env_spec in conda_envs.items():
        # Get and check conda environment type
        env_type = env_spec.get("type", None)
        if not check_env_type(env_type):
            continue

        # Get desired packages
        conda_packages = env_spec.get("conda_packages", {})
        pip_packages = env_spec.get("pip_packages", [])
        if not conda_packages and not pip_packages:
            Logger.step(
                f"Skipping installation of conda environment '{env_name}', as no packages are specified",
                warning=True,
            )
            continue

        # Get channels
        channels = env_spec.get("channels", [])

        # Environment config file
        env_file = {
            "name": env_name,
            "channels": channels,
            "dependencies": conda_packages,
        }
        if pip_packages:
            env_file["dependencies"].append("pip")
            env_file["dependencies"].append({"pip": pip_packages})

        env_yaml_path = NamedTemporaryFile(delete=False, suffix=".yaml").name
        with open(env_yaml_path, "w") as f:
            YAML().dump(env_file, f)

        # Executable command
        conda_cmd = [
            conda_exe[env_type],
            "env",
            "create",
            "-y",
            "-f",
            env_yaml_path,
        ]

        # Check if environment already exists
        check_cmd = [
            conda_exe[env_type],
            "run",
            "-n",
            env_name,
            "echo",
            "Environment exists",
        ]
        result = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
        )
        if (
            result.returncode == 0
            and "--update" not in remaining_args
            and not force
        ):
            Logger.step(
                f"Environment '{env_name}' already exists - Skipping creation",
                warning=True,
            )
            continue

        # Handle --update flag
        if "--update" in remaining_args:
            conda_cmd = ["update" if x == "create" else x for x in conda_cmd]
        else:
            if force:
                result = subprocess.run(
                    [conda_exe[env_type], "env", "remove", "-n", env_name],
                    capture_output=True,
                    text=True,
                )
                if not result.returncode == 0:
                    Logger.step(
                        f"Failed to remove existing environment '{env_name}' - Skipping creation",
                        warning=True,
                    )
                    continue
            else:
                Logger.step(
                    f"Environment '{env_name}' already exists - Skipping creation",
                    warning=True,
                )
                continue

        # Create environment
        Logger.step(
            f"Creating environment '{env_name}' with {env_type}...",
        )
        result = subprocess.run(conda_cmd)
        if result.returncode != 0:
            Logger.step(
                f"Failed to create environment '{env_name}'", warning=True
            )
        else:
            Logger.step(f"Successfully created environment '{env_name}'")

        # Cleanup
        os.remove(env_yaml_path)
