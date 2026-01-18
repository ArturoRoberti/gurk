import pytest

from gurk.lib.utils.common import stream_print
from gurk.lib.utils.plugins import iter_scripts
from gurk.lib.utils.scripts import check_script_blocks


def test_package_scripts() -> None:
    """Test that the package scripts are valid."""
    errors = []
    for path in iter_scripts():
        errors.extend(check_script_blocks(path))

    if errors:
        for error in errors:
            stream_print(f"ERROR: {error}", stderr=True)
        pytest.fail("One or more scripts contain disallowed top-level blocks")
