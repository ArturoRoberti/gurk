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

from gurk.lib.core.plugins import get_local_plugin_version
from gurk.lib.shared.remotes import determine_ref, parse_git_query
from gurk.lib.utils import GIT_QUERY_VERSIONING_FIELDS, typecheck

from ...utils import (
    TEMPLATE_PLUGIN_VERSIONING,
    ExpectedOutcome,
    PytestUnexpectedException,
)

if TYPE_CHECKING:
    from ..preparation import PreparedPluginRegistration
else:
    from typing import Any, TypeAlias

    PreparedPluginRegistration: TypeAlias = Any


@typecheck
def expected_outcome_pull_remote_specification(
    registration: PreparedPluginRegistration, specification: str
) -> ExpectedOutcome:
    """
    Determine the expected outcome of pulling a remote plugin specification based on the current registration and the specification being pulled.

    :param registration: The current plugin registration (if any).
    :type registration: PreparedPluginRegistration
    :param specification: The remote plugin specification being pulled.
    :type specification: str
    :return: The expected outcome of the pull operation.
    :rtype: ExpectedOutcome
    """
    parsed = parse_git_query(specification)
    if not registration.is_registered:
        # No plugin is registered, thus any specification should be valid
        return ExpectedOutcome.SUCCESS
    elif (
        registration.entry["local"] is None
        and registration.entry["remote"] is None
    ):
        # A registration exists but has no local or remote source
        raise PytestUnexpectedException(
            "Invalid registration: 'local' or 'remote' must be set if a registration exists."
        )
    elif registration.entry["local"] is None:
        # A registration exists but is not installed - expect successful override
        return ExpectedOutcome.SUCCESS
    elif registration.entry["remote"] is None:
        # A registration exists but has no remote (i.e. likely a different plugin)
        return ExpectedOutcome.PARTIAL
    elif not any(parsed[f] for f in GIT_QUERY_VERSIONING_FIELDS):
        # No version was specified, thus any already registered version should work
        return ExpectedOutcome.SUCCESS
    elif (
        determine_ref(registration.entry["remote"], to_commit=True)
        == TEMPLATE_PLUGIN_VERSIONING["commit"]["exists"]
    ):
        # The registered plugin matches the specified plugin version
        return ExpectedOutcome.SUCCESS
    else:
        # The registered plugin does not match the specified plugin version
        return ExpectedOutcome.PARTIAL


@typecheck
def expected_outcome_pull_local_path_specification(
    registration: PreparedPluginRegistration, specification: str
) -> ExpectedOutcome:
    """
    Determine the expected outcome of pulling a local plugin specification based on the current registration and the specification being pulled.

    :param registration: The current plugin registration (if any).
    :type registration: PreparedPluginRegistration
    :param specification: The local plugin specification being pulled.
    :type specification: str
    :return: The expected outcome of the pull operation.
    :rtype: ExpectedOutcome
    """
    specified_version = get_local_plugin_version(specification)
    if not registration.is_registered:
        # No plugin is registered, thus any specification should be valid
        return ExpectedOutcome.SUCCESS
    elif (
        registration.entry["local"] is None
        and registration.entry["remote"] is None
    ):
        # A registration exists but has no local or remote source
        raise PytestUnexpectedException(
            "Invalid registration: 'local' or 'remote' must be set if a registration exists."
        )
    elif registration.entry["remote"] is not None:
        # A registration exists but has a remote (i.e. likely a different plugin)
        return ExpectedOutcome.PARTIAL
    elif (
        specified_version is not None
        and get_local_plugin_version(registration.entry["local"])
        == specified_version
    ):
        # The registered plugin matches the specified plugin version
        return ExpectedOutcome.SUCCESS
    else:
        # The registered plugin does not match the specified plugin version
        return ExpectedOutcome.PARTIAL
