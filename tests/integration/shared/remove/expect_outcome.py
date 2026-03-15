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

from gurk.lib.utils import typecheck

from ...utils import ExpectedOutcome, RegistryKind

if TYPE_CHECKING:
    from ..preparation import PreparedPluginRegistration
else:
    from typing import Any, TypeAlias

    PreparedPluginRegistration: TypeAlias = Any


@typecheck
def expected_outcome_remove_name_specification(
    registration: PreparedPluginRegistration, specification: str
) -> ExpectedOutcome:
    """
    Determine the expected outcome of removing a plugin based on the current registration and the name specification being removed.

    :param registration: The current plugin registration (if any).
    :type registration: PreparedPluginRegistration
    :param specification: The name specification being removed.
    :type specification: str
    :return: The expected outcome of the remove operation.
    :rtype: ExpectedOutcome
    """
    if not registration.is_registered:
        # No plugin is registered, thus any removal should be invalid
        return ExpectedOutcome.PARTIAL
    elif registration.kind == RegistryKind.PRIVATE:
        # Private registry entries should not be removable
        return ExpectedOutcome.PARTIAL
    else:
        # Expected success (regardless of venv existence)
        return ExpectedOutcome.SUCCESS
