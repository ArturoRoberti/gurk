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

from pathlib import Path

import pytest

from gurk.lib.shared.remotes import edit_url
from gurk.lib.utils import GURK_METADATA_FILENAME

from .shared import (
    PreparedPluginRegistration,
    assert_outcome,
    expected_outcome_pull_local_path_specification,
    expected_outcome_pull_remote_specification,
    gurk_pull,
)
from .utils import (
    TEMPLATE_PLUGIN_REMOTE,
    ExpectedOutcome,
    PytestUnexpectedException,
)


################################################################################################
######################################### Local Plugin #########################################
################################################################################################
def test_pull_local_plugin_validly(
    prepared_plugin_registration: PreparedPluginRegistration,
    valid_local_plugin_specification: str,
    local_plugin_path: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test pulling a local plugin with a valid specification."""
    # Infer expected outcome
    expected_outcome = expected_outcome_pull_local_path_specification(
        prepared_plugin_registration, local_plugin_path
    )

    # Attempt to pull the local plugin specification
    e, captured = gurk_pull([valid_local_plugin_specification], capsys)
    assert_outcome(e, captured, expected_outcome)


def test_pull_local_plugin_invalidly(
    missing_plugin_registration: PreparedPluginRegistration,
    invalid_local_plugin_specification: str,
    local_plugin_path: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test pulling a local plugin with an invalid specification."""
    # Attempt to pull the local plugin specification
    e, captured = gurk_pull([invalid_local_plugin_specification], capsys)
    assert_outcome(e, captured, ExpectedOutcome.PARTIAL)


def test_pull_invalid_local_plugin(
    missing_plugin_registration: PreparedPluginRegistration,
    local_plugin_path: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test pulling a local plugin that is invalid."""
    # Make the plugin invalid by removing the metadata file
    metadata_file = Path(local_plugin_path) / GURK_METADATA_FILENAME
    if metadata_file.is_file():
        metadata_file.unlink()
    else:
        raise PytestUnexpectedException(
            f"Expected metadata file at {metadata_file} was not found to set up the test."
        )

    # Attempt to pull the local plugin
    e, captured = gurk_pull([local_plugin_path], capsys)
    assert_outcome(e, captured, ExpectedOutcome.PARTIAL)


################################################################################################
######################################### Remote Plugin ########################################
################################################################################################
def test_pull_remote_plugin_validly(
    prepared_plugin_registration: PreparedPluginRegistration,
    valid_remote_plugin_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test pulling a remote plugin with a valid specification."""
    # Infer expected outcome
    expected_outcome = expected_outcome_pull_remote_specification(
        prepared_plugin_registration, valid_remote_plugin_specification
    )

    # Attempt to pull the remote plugin specification
    e, captured = gurk_pull([valid_remote_plugin_specification], capsys)
    assert_outcome(e, captured, expected_outcome)


def test_pull_remote_plugin_invalidly(
    missing_plugin_registration: PreparedPluginRegistration,
    invalid_remote_plugin_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test pulling a remote plugin with an invalid specification."""
    # Attempt to pull the remote plugin specification
    e, captured = gurk_pull([invalid_remote_plugin_specification], capsys)
    assert_outcome(e, captured, ExpectedOutcome.PARTIAL)


def test_pull_invalid_remote_plugin(
    missing_plugin_registration: PreparedPluginRegistration,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test pulling a remote plugin that is invalid."""
    # Use a known invalid branch specification
    invalid_remote = edit_url(
        TEMPLATE_PLUGIN_REMOTE, branch="pytest/invalid_manifest"
    )

    # Attempt to pull the remote plugin
    e, captured = gurk_pull([invalid_remote], capsys)
    assert_outcome(e, captured, ExpectedOutcome.PARTIAL)
