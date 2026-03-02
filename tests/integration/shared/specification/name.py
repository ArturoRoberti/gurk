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

from gurk.lib.shared.remotes import edit_url

from ...utils import PYTEST_PLUGIN_NAME, TEMPLATE_PLUGIN_VERSIONING

VALID_NAME_SPECIFICATION_OPTIONS = {PYTEST_PLUGIN_NAME}  # simple plugin name
INVALID_NAME_SPECIFICATION_OPTIONS = {
    edit_url(
        PYTEST_PLUGIN_NAME,
        version=TEMPLATE_PLUGIN_VERSIONING["version"]["exists"],
    ),  # with version
    "non-existent-name",  # non-existent name
}
