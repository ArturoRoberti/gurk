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
