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
    expected_outcome_help,
    gurk_help,
)
from .utils import ExpectedOutcome


################################################################################################
#################################### Informational Modes #######################################
################################################################################################
@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--available-plugins"],
        ["--available-tasks"],
        ["--structure"],
        ["--system-info"],
    ],
)
def test_help_informational(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that informational 'gurk help' modes always succeed."""
    e, captured = gurk_help(argv, capsys)
    assert_outcome(e, captured, ExpectedOutcome.SUCCESS)


################################################################################################
####################################### Plugin Help ############################################
################################################################################################
def test_help_plugins(
    prepared_plugin_registration: PreparedPluginRegistration,
    valid_plugin_name_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk help --plugins <name>' with a valid plugin name under various
    registration conditions."""
    expected_outcome = expected_outcome_help(
        prepared_plugin_registration, valid_plugin_name_specification
    )
    e, captured = gurk_help(
        ["--plugins", valid_plugin_name_specification], capsys
    )
    assert_outcome(e, captured, expected_outcome)


################################################################################################
######################################## Task Help #############################################
################################################################################################
def test_help_tasks(
    prepared_plugin_registration: PreparedPluginRegistration,
    valid_plugin_name_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 'gurk help --tasks <task>' with a known always-available task."""
    expected_outcome = expected_outcome_help(
        prepared_plugin_registration, valid_plugin_name_specification
    )
    e, captured = gurk_help(
        ["--tasks", f"{valid_plugin_name_specification}/some-task"], capsys
    )
    assert_outcome(e, captured, expected_outcome)
