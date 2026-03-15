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

from .common import PYTEST_PLUGIN_NAME, PYTEST_PLUGIN_PATH
from .template import (
    TEMPLATE_PLUGIN_REMOTE,
    TEMPLATE_PLUGIN_SPECIFICATION_OPTIONS,
    TEMPLATE_PLUGIN_VERSIONING,
)

__all__ = [
    "PYTEST_PLUGIN_NAME",
    "PYTEST_PLUGIN_PATH",
    "TEMPLATE_PLUGIN_REMOTE",
    "TEMPLATE_PLUGIN_SPECIFICATION_OPTIONS",
    "TEMPLATE_PLUGIN_VERSIONING",
]
