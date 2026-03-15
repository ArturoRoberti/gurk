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

import pytest

from .shared import (
    PreparedPluginRegistration,
    assert_outcome,
    expected_outcome_run_local_specification,
    expected_outcome_run_name_specification,
    expected_outcome_run_remote_specification,
    gurk_run,
)
from .utils import ExpectedOutcome


################################################################################################
####################################### Local Path Spec ########################################
################################################################################################
def test_run_local_plugin_validly(
    prepared_plugin_registration: PreparedPluginRegistration,
    local_plugin_path: str,
    run_plugin_specification_option: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk run <local-path>' under various registration conditions.

    When there is no conflict the plugin is installed on-the-fly and its default
    option (a simple bash echo task from the template) is executed.
    """
    expected_outcome = expected_outcome_run_local_specification(
        prepared_plugin_registration, local_plugin_path
    )

    e, captured = gurk_run(
        [local_plugin_path + run_plugin_specification_option], capsys
    )
    assert_outcome(e, captured, expected_outcome)


def test_run_local_plugin_invalidly(
    missing_plugin_registration: PreparedPluginRegistration,
    invalid_local_plugin_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk run <local-path>' with an invalid local path specification.

    Invalid local paths are rejected by parse_specification() at argparse
    type-validation time, causing argparse to exit with code 2.
    """
    e, captured = gurk_run([invalid_local_plugin_specification], capsys)
    assert_outcome(e, captured, ExpectedOutcome.ARGPARSE)


################################################################################################
####################################### Remote Git Spec ########################################
################################################################################################
def test_run_remote_plugin_validly(
    prepared_plugin_registration: PreparedPluginRegistration,
    valid_remote_plugin_specification: str,
    run_plugin_specification_option: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk run <remote-url>' under various registration conditions."""
    expected_outcome = expected_outcome_run_remote_specification(
        prepared_plugin_registration, valid_remote_plugin_specification
    )

    e, captured = gurk_run(
        [valid_remote_plugin_specification + run_plugin_specification_option],
        capsys,
    )
    assert_outcome(e, captured, expected_outcome)


def test_run_remote_plugin_invalidly(
    missing_plugin_registration: PreparedPluginRegistration,
    invalid_remote_plugin_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk run <remote-url>' with an invalid remote specification.

    Invalid git query specs (missing/non-existent branch/version, or multiple
    versioning fields) are parsed by argparse but rejected by install_plugin(),
    causing 'gurk run' to call fatal() and exit with code 1.
    """
    e, captured = gurk_run([invalid_remote_plugin_specification], capsys)
    assert_outcome(e, captured, ExpectedOutcome.ARGPARSE)


################################################################################################
####################################### Plugin Name Spec #######################################
################################################################################################
def test_run_named_plugin_validly(
    prepared_plugin_registration: PreparedPluginRegistration,
    valid_plugin_name_specification: str,
    run_plugin_specification_option: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk run <plugin-name>' under various registration conditions.

    For a name spec, parse_specification() calls is_plugin_installed(name,
    require_venv=True). If the check fails, argparse exits with code 2
    (ARGPARSE). When it passes the plugin is executed.
    """
    expected_outcome = expected_outcome_run_name_specification(
        prepared_plugin_registration, valid_plugin_name_specification
    )

    e, captured = gurk_run(
        [valid_plugin_name_specification + run_plugin_specification_option],
        capsys,
    )
    assert_outcome(e, captured, expected_outcome)


def test_run_named_plugin_invalidly(
    missing_plugin_registration: PreparedPluginRegistration,
    invalid_plugin_name_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk run <plugin-name>' with an invalid or non-existent name.

    Invalid name specs are rejected by parse_specification() at argparse
    type-validation time, causing argparse to exit with code 2.
    """
    e, captured = gurk_run([invalid_plugin_name_specification], capsys)
    assert_outcome(e, captured, ExpectedOutcome.ARGPARSE)
