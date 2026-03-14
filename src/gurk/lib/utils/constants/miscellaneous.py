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

from pathlib import Path

from .common import PACKAGE_NAME, PACKAGE_SRC_PATH

PACKAGE_HOME_PATH = Path.home() / f".{PACKAGE_NAME}"
GURK_LOCKFILE_PATH = PACKAGE_HOME_PATH / "core.lock"
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
