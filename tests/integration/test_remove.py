import pytest

from .shared import (
    VALID_GIT_QUERY_SPECIFICATION_OPTIONS,
    VALID_LOCAL_PATH_SPECIFICATION_OPTIONS,
    PreparedPluginRegistration,
    assert_outcome,
    expected_outcome_remove_name_specification,
    gurk_remove,
)
from .utils import ExpectedOutcome


def test_remove_plugin_validly(
    prepared_plugin_registration: PreparedPluginRegistration,
    valid_plugin_name_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test removing a plugin under various conditions."""
    # Infer expected outcome
    expected_outcome = expected_outcome_remove_name_specification(
        prepared_plugin_registration, valid_plugin_name_specification
    )

    # Attempt to remove the plugin specification
    e, captured = gurk_remove([valid_plugin_name_specification], capsys)
    assert_outcome(e, captured, expected_outcome)


def test_remove_plugin_invalidly(
    prepared_plugin_registration: PreparedPluginRegistration,
    invalid_plugin_name_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test removing a plugin with an invalid name."""
    # Attempt to remove the plugin specification
    e, captured = gurk_remove([invalid_plugin_name_specification], capsys)
    assert_outcome(e, captured, ExpectedOutcome.PARTIAL)


@pytest.mark.parametrize(
    "wrong_plugin_specification_type",
    [
        next(iter(options))
        for options in [
            VALID_LOCAL_PATH_SPECIFICATION_OPTIONS,
            VALID_GIT_QUERY_SPECIFICATION_OPTIONS,
        ]
    ],
)
def test_remove_plugin_wrong_specification_type(
    missing_plugin_registration: PreparedPluginRegistration,
    wrong_plugin_specification_type: str,
    capsys: pytest.CaptureFixture[str],
):
    """Test removing a plugin via a wrong specification type."""
    # Attempt to remove the plugin specification
    e, captured = gurk_remove([wrong_plugin_specification_type], capsys)
    assert_outcome(e, captured, ExpectedOutcome.PARTIAL)
