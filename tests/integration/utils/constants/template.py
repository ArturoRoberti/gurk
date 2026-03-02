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

from typing import TYPE_CHECKING

from gurk.lib.shared.remotes import (
    determine_ref,
    edit_url,
    get_default_branch,
    get_latest_version,
)

from ..types import PytestUnexpectedException

if TYPE_CHECKING:
    from ..types import PluginVersioning
else:
    from typing import TypeAlias

    PluginVersioning: TypeAlias = dict[str, dict[str, str]]

# template plugin data
TEMPLATE_PLUGIN_REMOTE = (
    "https://github.com/ArturoRoberti/gurk_template_plugin.git"
)
latest_version = get_latest_version(TEMPLATE_PLUGIN_REMOTE)
latest_version_commit = determine_ref(
    edit_url(TEMPLATE_PLUGIN_REMOTE, version=latest_version), to_commit=True
)
default_branch = get_default_branch(TEMPLATE_PLUGIN_REMOTE)
latest_default_commit = determine_ref(
    edit_url(TEMPLATE_PLUGIN_REMOTE, branch=default_branch), to_commit=True
)
if not all((latest_version, latest_default_commit, latest_version_commit)):
    raise PytestUnexpectedException(
        "Failed to retrieve necessary versioning information for the template "
        f"plugin - latest_version: {latest_version}, latest_default_commit: "
        f"{latest_default_commit}, latest_version_commit: {latest_version_commit}."
    )
elif latest_default_commit != latest_version_commit:
    raise PytestUnexpectedException(
        f"Latest version '{latest_version}' does not point to the latest "
        "commit for the template plugin - latest_version_commit: "
        f"{latest_version_commit}, latest_default_commit: {latest_default_commit}."
    )
TEMPLATE_PLUGIN_VERSIONING: PluginVersioning = {
    "version": {"exists": latest_version, "missing": "missing_version"},
    "branch": {"exists": default_branch, "missing": "missing_branch"},
    "commit": {"exists": latest_default_commit, "missing": "missing_commit"},
}
