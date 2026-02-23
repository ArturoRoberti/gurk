from typing import TYPE_CHECKING

from gurk.lib.core.plugins import get_local_plugin_version

from ...utils import ExpectedOutcome, PytestUnexpectedException

if TYPE_CHECKING:
    from ..prepared_registration import PreparedPluginRegistration
else:
    from typing import Any, TypeAlias

    PreparedPluginRegistration: TypeAlias = Any


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
    elif registration.entry["remote"] is not None:
        # A registration exists but has a remote (i.e. likely a different plugin)
        return ExpectedOutcome.PARTIAL
    elif registration.entry["local"] is None:
        # A registration exists with no source
        raise PytestUnexpectedException(
            "Invalid registration: 'local' or 'remote' must be set if a registration exists."
        )
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
