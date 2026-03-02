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

from .answers import NO_ANSWERS, YES_ANSWERS
from .common import (
    GURK_VERSION,
    PACKAGE_CACHE_PATH,
    PACKAGE_NAME,
    PACKAGE_SRC_PATH,
    PACKAGE_TESTS_PATH,
    PIPX_PYTHON_PATH,
)
from .miscellaneous import (
    GURK_MANIFEST_FILENAME,
    GURK_METADATA_FILENAME,
    PACKAGE_BASH_HELPERS_PATH,
    PACKAGE_HOME_PATH,
    PACKAGE_VENVS_PATH,
    RUNNER_SPECIFIC_TASKS,
    SETUP_DONE_FILE,
)
from .remotes import (
    GIT_MIRRORS_DIR,
    GIT_QUERY_VERSIONING_FIELDS,
    PACKAGE_GIT_CACHE_METADATA_PATH,
)
from .template import TEMPLATE_PLUGIN_NAME, TEMPLATE_PLUGIN_PATH

__all__ = [
    "GIT_MIRRORS_DIR",
    "GIT_QUERY_VERSIONING_FIELDS",
    "GURK_MANIFEST_FILENAME",
    "GURK_METADATA_FILENAME",
    "GURK_VERSION",
    "NO_ANSWERS",
    "PACKAGE_BASH_HELPERS_PATH",
    "PACKAGE_CACHE_PATH",
    "PACKAGE_GIT_CACHE_METADATA_PATH",
    "PACKAGE_HOME_PATH",
    "PACKAGE_NAME",
    "PACKAGE_SRC_PATH",
    "PACKAGE_TESTS_PATH",
    "PACKAGE_VENVS_PATH",
    "PIPX_PYTHON_PATH",
    "RUNNER_SPECIFIC_TASKS",
    "SETUP_DONE_FILE",
    "TEMPLATE_PLUGIN_NAME",
    "TEMPLATE_PLUGIN_PATH",
    "YES_ANSWERS",
]
