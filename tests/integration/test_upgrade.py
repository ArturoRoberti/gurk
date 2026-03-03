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
    VALID_GIT_QUERY_SPECIFICATION_OPTIONS,
    VALID_LOCAL_PATH_SPECIFICATION_OPTIONS,
    PreparedPluginRegistration,
    assert_outcome,
    expected_outcome_upgrade_name_specification,
    gurk_upgrade,
)
from .utils import ExpectedOutcome


def test_upgrade_plugin_validly(
    prepared_plugin_registration: PreparedPluginRegistration,
    valid_plugin_name_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test upgrading a plugin under various conditions."""
    # Infer expected outcome
    expected_outcome = expected_outcome_upgrade_name_specification(
        prepared_plugin_registration, valid_plugin_name_specification
    )

    # Attempt to upgrade the plugin specification
    e, captured = gurk_upgrade([valid_plugin_name_specification], capsys)
    assert_outcome(e, captured, expected_outcome)


def test_upgrade_plugin_invalidly(
    prepared_plugin_registration: PreparedPluginRegistration,
    invalid_plugin_name_specification: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test upgrading a plugin with an invalid name."""
    # Attempt to upgrade the plugin specification
    e, captured = gurk_upgrade([invalid_plugin_name_specification], capsys)
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
def test_upgrade_plugin_wrong_specification_type(
    missing_plugin_registration: PreparedPluginRegistration,
    wrong_plugin_specification_type: str,
    capsys: pytest.CaptureFixture[str],
):
    """Test upgrading a plugin via a wrong specification type."""
    # Attempt to upgrade the plugin specification
    e, captured = gurk_upgrade([wrong_plugin_specification_type], capsys)
    assert_outcome(e, captured, ExpectedOutcome.PARTIAL)
