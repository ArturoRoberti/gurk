from typing import TYPE_CHECKING

from gurk.lib.shared.remotes import determine_ref, parse_git_query
from gurk.lib.utils import GIT_QUERY_VERSIONING_FIELDS, typecheck

from ...utils import EXAMPLE_PLUGIN_VERSIONING, ExpectedOutcome

if TYPE_CHECKING:
    from ..prepared_registration import PreparedPluginRegistration
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
        == EXAMPLE_PLUGIN_VERSIONING["commit"]["exists"]
    ):
        # The registered plugin matches the specified plugin version
        return ExpectedOutcome.SUCCESS
    else:
        # The registered plugin does not match the specified plugin version
        return ExpectedOutcome.PARTIAL
