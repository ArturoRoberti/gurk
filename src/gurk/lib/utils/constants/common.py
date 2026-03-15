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

import sys
from importlib import resources
from importlib.metadata import version
from pathlib import Path

from platformdirs import (
    user_cache_path,
    user_config_path,
    user_data_path,
    user_log_path,
)

# Package constants
PACKAGE_NAME = "gurk"
GURK_VERSION = version(PACKAGE_NAME)
PACKAGE_SRC_PATH = Path(resources.files(PACKAGE_NAME)).expanduser().resolve()
PIPX_PYTHON_PATH = Path(sys.executable)

# Package directories
PACKAGE_CACHE_PATH = user_cache_path(PACKAGE_NAME, ensure_exists=True)
PACKAGE_CONFIG_PATH = user_config_path(PACKAGE_NAME, ensure_exists=True)
PACKAGE_DATA_PATH = user_data_path(PACKAGE_NAME, ensure_exists=True)
PACKAGE_LOG_PATH = user_log_path(PACKAGE_NAME, ensure_exists=True)
