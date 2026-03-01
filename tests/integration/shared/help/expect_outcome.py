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
