from pathlib import Path

from .common import PACKAGE_NAME, PACKAGE_SRC_PATH

PACKAGE_HOME_PATH = Path.home() / f".{PACKAGE_NAME}"
PACKAGE_VENVS_PATH = PACKAGE_HOME_PATH / "venvs"
PACKAGE_VENVS_PATH.mkdir(parents=True, exist_ok=True)

SETUP_DONE_FILE = PACKAGE_HOME_PATH / "setup.done"

PACKAGE_BASH_HELPERS_PATH = (
    PACKAGE_SRC_PATH / "plugin_helpers" / "bash" / "helpers.bash"
)

GURK_MANIFEST_FILENAME = "gurk-manifest.yaml"
GURK_METADATA_FILENAME = "pyproject.toml"

# Explanations:
# - nvidia/install-isaaclab: Hangs (may be an issue with the install itself, not the runner)
# - nvidia/install-isaacsim: Takes too long (~30 mins); costs too much CI time - purely practical
# - nvidia/install-nvidia-driver: Cannot use 'modprobe nvidia'
# - ros/install-ros: Fails due to missing setup script (may be an issue with the install itself, not the runner)
RUNNER_SPECIFIC_TASKS = [
    "nvidia/install-isaaclab",
    "nvidia/install-isaacsim",
    "nvidia/install-nvidia-driver",
    "ros/install-ros",
]
