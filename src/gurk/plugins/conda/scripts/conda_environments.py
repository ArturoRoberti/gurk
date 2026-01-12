import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import NotRequired, TypedDict

import commentjson
from ruamel.yaml import YAML

from gurk import Logger, parse_task_args, run_script_function


def install_conda_environments(*args: list[str]) -> None:
    """
    Install packages into Conda environments (no custom env directory).
    """
    # Parse task args
    task_args = parse_task_args(args)

    # Typing helper classes
    class CondaEnv(TypedDict):
        # fmt: off
        type:           str                   # "conda", "mamba"
        conda_packages: dict[str, list[str]]  # package-name -> [channels]
        pip_packages:   NotRequired[list[str]]
        # fmt: on

    # Get conda environments info
    conda_envs: dict[str, CondaEnv] = commentjson.load(
        task_args.config_file.open("r", encoding="utf-8")
    )
    if not conda_envs:
        Logger.step(
            "Skipping installation of conda environments, as no environments are specified",
        )
        return

    # Check if conda types are installed
    conda_exe = {"conda": None, "mamba": None}
    for conda_type in conda_exe.keys():
        result = run_script_function(
            script=Path(__file__).parent / "checks.bash",
            function=f"check_install_{conda_type}",
            run=True,
            capture_output=True,
        )
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
            and not task_args.conda_update_environments
            and not task_args.force
        ):
            Logger.step(
                f"Environment '{env_name}' already exists - Skipping creation",
                warning=True,
            )
            continue

        # Handle --update flag
        if task_args.conda_update_environments:
            conda_cmd = ["update" if x == "create" else x for x in conda_cmd]
        else:
            if task_args.force:
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
