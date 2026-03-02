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

from ...utils import ExpectedOutcome

if TYPE_CHECKING:
    from ..preparation import PreparedPluginRegistration
else:
    from typing import Any, TypeAlias

    PreparedPluginRegistration: TypeAlias = Any


def expected_outcome_help(
    registration: PreparedPluginRegistration, specification: str
) -> ExpectedOutcome:
    """
    Determine the expected outcome of 'gurk help --plugins <specification>' based
    on the current registration state and the specification being queried.

    'gurk help' calls is_plugin_installed(plugin_name, require_venv=True), so the
    plugin must be both locally installed and have a virtual environment. Specifications
    that do not refer to the registered test plugin (e.g. invalid or missing names)
    are never found and always yield PARTIAL.

    :param registration: The current plugin registration (if any).
    :type registration: PreparedPluginRegistration
    :param specification: The plugin specification (name) being queried.
    :type specification: str
    :return: The expected outcome of the help operation.
    :rtype: ExpectedOutcome
    """
    if registration.is_installed:
        # The plugin is installed, so any valid specification should succeed
        return ExpectedOutcome.SUCCESS
    else:
        # The plugin is not installed, so even a valid specification should yield PARTIAL
        return ExpectedOutcome.PARTIAL
