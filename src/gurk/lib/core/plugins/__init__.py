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

from .check import check_local_plugin
from .core import (
    create_plugin_venv,
    install_plugin,
    is_plugin_installed,
    remove_plugin,
    upgrade_plugin,
)
from .getters import (
    get_available_plugin_tasks,
    get_plugin_data,
    get_raw_plugin_manifest,
    get_relevant_plugin_files,
    get_resolved_plugin_manifest,
    iter_configs,
    iter_scripts,
)
from .gurk_argparser import (
    DefaultNamespace,
    GurkArgumentParser,
    TaskParserNamespace,
)
from .versioning import (
    get_local_plugin_version,
    get_plugin_version,
    get_remote_plugin_version,
)
from .virtual_environments import (
    get_venv_dir,
    get_venv_gurk_version,
    remove_venv,
    venv_exists,
)

__all__ = [
    "DefaultNamespace",
    "GurkArgumentParser",
    "TaskParserNamespace",
    "check_local_plugin",
    "create_plugin_venv",
    "get_available_plugin_tasks",
    "get_local_plugin_version",
    "get_plugin_data",
    "get_plugin_version",
    "get_raw_plugin_manifest",
    "get_relevant_plugin_files",
    "get_remote_plugin_version",
    "get_resolved_plugin_manifest",
    "get_venv_dir",
    "get_venv_gurk_version",
    "install_plugin",
    "is_plugin_installed",
    "iter_configs",
    "iter_scripts",
    "remove_plugin",
    "remove_venv",
    "upgrade_plugin",
    "venv_exists",
]
