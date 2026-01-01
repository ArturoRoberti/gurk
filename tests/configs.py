# TODO: Figure out why a sudo pwd is still being asked for when running this (manually)

import subprocess
from typing import Optional

import commentjson
import pytest

from cmstp.cli import core
from cmstp.utils.common import DEFAULT_CONFIG_FILE, get_config_path
from cmstp.utils.yaml import load_yaml

from .utils import _get_sudo_askpass


def test_package_configs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the package configuration files are valid."""

    # Disable/Replace prompts
    monkeypatch.setattr(core, "get_sudo_askpass", _get_sudo_askpass)
    monkeypatch.setattr(
        core.CoreCliProcessor, "prompt_setup", lambda self: None
    )
    monkeypatch.setattr(core.Scheduler, "run", lambda self: None)

    # Process tasks (without running them) using the package configs
    with pytest.raises(SystemExit) as e:
        core.main(
            argv=["--disable-preparation", "-v"],
            prog="",
            description="",
            cmd="install",
        )
    assert e.value.code == 0, "Core exited with non-zero code for configs"

    # Check all task config files are valid
    default_config = load_yaml(DEFAULT_CONFIG_FILE)
    for task_name, task in default_config.items():
        if task_name.startswith("_"):
            # Skip helpers
            continue

        config_file: Optional[str] = task["config_file"]
        if config_file:
            full_path = get_config_path(config_file, task_name.split("-")[0])
            if not full_path.is_file():
                pytest.fail(
                    f"Config file '{config_file}' for task '{task_name}' does not exist"
                )
            elif config_file.endswith((".json", ".jsonc")):
                try:
                    with open(full_path, "r") as f:
                        commentjson.load(f)
                except Exception as ex:
                    pytest.fail(
                        f"Failed to load JSON config file '{config_file}' for task '{task_name}': {ex}"
                    )
            elif config_file.endswith((".yml", ".yaml")):
                try:
                    load_yaml(full_path)
                except Exception as ex:
                    pytest.fail(
                        f"Failed to load YAML config file '{config_file}' for task '{task_name}': {ex}"
                    )
            elif config_file.endswith(".bash"):
                # Basic syntax check for bash scripts
                result = subprocess.run(
                    ["bash", "-n", str(full_path)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    pytest.fail(
                        f"Syntax error in bash config file '{config_file}' for task '{task_name}': {result.stderr}"
                    )
