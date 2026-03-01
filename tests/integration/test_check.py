from pathlib import Path

import pytest

from gurk.lib.utils import GURK_METADATA_FILENAME

from .shared import assert_outcome, gurk_check
from .utils import ExpectedOutcome, PytestUnexpectedException


def test_check_valid_plugin(
    local_plugin_path: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that a validly structured local plugin passes the check."""
    e, captured = gurk_check([local_plugin_path], capsys)
    assert_outcome(e, captured, ExpectedOutcome.SUCCESS)


def test_check_invalid_plugin(
    local_plugin_path: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that a plugin with missing metadata fails the check."""
    metadata_file = Path(local_plugin_path) / GURK_METADATA_FILENAME
    if metadata_file.is_file():
        metadata_file.unlink()
    else:
        raise PytestUnexpectedException(
            f"Expected metadata file at {metadata_file} was not found to set up the test."
        )

    e, captured = gurk_check([local_plugin_path], capsys)
    assert_outcome(e, captured, ExpectedOutcome.FAILURE)


def test_check_nonexistent_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that a non-existent path fails the check."""
    e, captured = gurk_check(["non-existent-plugin-path"], capsys)
    assert_outcome(e, captured, ExpectedOutcome.FAILURE)
