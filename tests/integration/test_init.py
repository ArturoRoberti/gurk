import pytest

from .shared import PreparedPluginRegistration, assert_outcome, gurk_init
from .utils import ExpectedOutcome


def test_init_validly(
    prepared_plugin_registration: PreparedPluginRegistration,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk init' succeeds under various plugin registration conditions."""
    # 'gurk init' takes no positional arguments and always exits 0.
    e, captured = gurk_init([], capsys)
    assert_outcome(e, captured, ExpectedOutcome.SUCCESS)
