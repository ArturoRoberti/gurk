from typing import TYPE_CHECKING

from gurk.lib.utils import typecheck

from ...utils import ExpectedOutcome

if TYPE_CHECKING:
    from ..preparation import PreparedPluginRegistration
else:
    from typing import Any, TypeAlias

    PreparedPluginRegistration: TypeAlias = Any


@typecheck
def expected_outcome_upgrade_name_specification(
    registration: PreparedPluginRegistration, specification: str
) -> ExpectedOutcome:
    """
    Determine the expected outcome of removing a plugin based on the current registration and the name specification being upgraded.

    :param registration: The current plugin registration (if any).
    :type registration: PreparedPluginRegistration
    :param specification: The name specification being upgraded.
    :type specification: str
    :return: The expected outcome of the upgrade operation.
    :rtype: ExpectedOutcome
    """
    if not registration.is_registered:
        # No plugin is registered, thus any upgrade should be invalid
        return ExpectedOutcome.PARTIAL
    elif registration.entry["remote"] is None:
        # A registration exists but has no remote, thus cannot be upgraded
        return ExpectedOutcome.PARTIAL
    else:
        # Expected success (regardless of venv existence)
        return ExpectedOutcome.SUCCESS
