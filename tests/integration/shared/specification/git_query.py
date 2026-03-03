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

from ...utils import TEMPLATE_PLUGIN_REMOTE, TEMPLATE_PLUGIN_VERSIONING

# Valid specifications
VALID_GIT_QUERY_SPECIFICATION_OPTIONS = {
    TEMPLATE_PLUGIN_REMOTE
}  # simple remote
VALID_GIT_QUERY_SPECIFICATION_OPTIONS.update(  # existing/valid versioning fields
    {
        edit_url(TEMPLATE_PLUGIN_REMOTE, **{field: existences["exists"]})
        for field, existences in TEMPLATE_PLUGIN_VERSIONING.items()
    }
)

# Invalid specifications
INVALID_GIT_QUERY_SPECIFICATION_OPTIONS = (
    {  # missing/invalid versioning fields
        edit_url(TEMPLATE_PLUGIN_REMOTE, **{field: existences["missing"]})
        for field, existences in TEMPLATE_PLUGIN_VERSIONING.items()
    }
)
INVALID_GIT_QUERY_SPECIFICATION_OPTIONS.add(  # multiple versioning fields
    edit_url(
        TEMPLATE_PLUGIN_REMOTE,
        **{
            field: existences["exists"]
            for field, existences in TEMPLATE_PLUGIN_VERSIONING.items()
        },
    )
)
