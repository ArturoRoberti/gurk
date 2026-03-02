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

from gurk.cli import template


def gurk_template(argv: list[str]) -> None:
    """
    Helper function to execute the 'gurk template' command. As this should cause no errors, it asserts that the exit code is 0 and returns nothing.

    :param argv: List of command-line arguments to pass to 'gurk template'.
    :type argv: list[str]
    """
    with pytest.raises(SystemExit) as e:
        template.main(
            argv,
            prog="gurk template",
            description="Generate a plugin template in the current working directory.",
        )
    assert (
        e.value.code == 0
    ), f"Template generation failed with exit code {e.value.code}"
