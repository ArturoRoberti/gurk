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
from _pytest._code.code import ExceptionInfo
from _pytest.capture import CaptureFixture, CaptureResult

from gurk.cli import help as help_cli


def gurk_help(
    argv: list[str], capsys: CaptureFixture[str]
) -> tuple[ExceptionInfo[SystemExit], CaptureResult[str]]:
    """
    Helper function to execute the 'gurk help' command and capture its output.

    'gurk help' does not call done()/fatal() in most branches, so a fallback
    SystemExit(0) is raised when main() returns normally. This ensures the
    return type is always consistent with the other gurk_* helpers.

    :param argv: List of command-line arguments to pass to 'gurk help'.
    :type argv: list[str]
    :param capsys: Pytest fixture to capture stdout and stderr.
    :type capsys: CaptureFixture[str]
    :return: A tuple containing the exception info and captured output.
    :rtype: tuple[ExceptionInfo[SystemExit], CaptureResult[str]]
    """
    with pytest.raises(SystemExit) as e:
        help_cli.main(
            argv,
            prog="gurk help",
            description="Show help for gurk or its plugins.",
        )
        raise SystemExit(0)

    return e, capsys.readouterr()
