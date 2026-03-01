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
    elif registration.kind == RegistryKind.PACKAGE:
        # Package registry entries should not be removable
        return ExpectedOutcome.PARTIAL
    else:
        # Expected success (regardless of venv existence)
        return ExpectedOutcome.SUCCESS
