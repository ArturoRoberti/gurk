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

from copy import deepcopy
from itertools import product

from gurk.lib.shared.plugins import PluginRegistryEntry
from gurk.lib.shared.remotes import edit_url

from ...utils import (
    PYTEST_PLUGIN_NAME,
    TEMPLATE_PLUGIN_REMOTE,
    TEMPLATE_PLUGIN_VERSIONING,
    RegistryKind,
    bump_patch,
)

# 'registration'
remote = edit_url(
    TEMPLATE_PLUGIN_REMOTE,
    commit=TEMPLATE_PLUGIN_VERSIONING["commit"]["exists"],
)
REGISTRY_ENTRY_OPTIONS: list[PluginRegistryEntry | None] = [
    None,
    PluginRegistryEntry(local=None, remote=remote),
    PluginRegistryEntry(local=PYTEST_PLUGIN_NAME, remote=None),
    PluginRegistryEntry(local=PYTEST_PLUGIN_NAME, remote=remote),
]

# 'kind'
REGISTRY_KIND_OPTIONS = set(RegistryKind)

# 'venv_exists'
REGISTRY_VENVS_EXISTS_OPTIONS = {True, False}


# Full parameter combinations
def is_registration_valid(
    entry: PluginRegistryEntry | None, kind: RegistryKind, venv_exists: bool
) -> bool:
    """Determine if a given combination of registration entry and venv existence is valid."""
    if entry is None and venv_exists:
        # No registration but venv exists - invalid
        return False
    return True


PREPARED_PLUGIN_REGISTRATION_PARAMS = [  # Filter invalid entries
    (entry, kind, venv_exists)
    for entry, kind, venv_exists in product(
        REGISTRY_ENTRY_OPTIONS,
        REGISTRY_KIND_OPTIONS,
        REGISTRY_VENVS_EXISTS_OPTIONS,
    )
    if is_registration_valid(entry, kind, venv_exists)
]
# Collapse unregistered entries into one
unregistered_found = False
for entry, kind, venv_exists in deepcopy(PREPARED_PLUGIN_REGISTRATION_PARAMS):
    if entry is None:
        if not unregistered_found:
            unregistered_found = True
        else:
            PREPARED_PLUGIN_REGISTRATION_PARAMS.remove(
                (entry, kind, venv_exists)
            )

# Local plugin versions
existing_version = TEMPLATE_PLUGIN_VERSIONING["version"]["exists"]
LOCAL_PLUGIN_VERSIONS = {
    existing_version,  # Existing version
    bump_patch(existing_version),  # New version
}
