import pytest
from _pytest._code.code import ExceptionInfo
from _pytest.capture import CaptureFixture, CaptureResult

from gurk.cli import run


def gurk_run(
    argv: list[str], capsys: CaptureFixture[str]
) -> tuple[ExceptionInfo[SystemExit], CaptureResult[str]]:
    """
    Helper function to execute the 'gurk run' command and capture its output.

    :param argv: List of command-line arguments to pass to 'gurk run'.
    :type argv: list[str]
    :param capsys: Pytest fixture to capture stdout and stderr.
    :type capsys: CaptureFixture[str]
    :return: A tuple containing the exception info and captured output.
    :rtype: tuple[ExceptionInfo[SystemExit], CaptureResult[str]]
    """
    with pytest.raises(SystemExit) as e:
        run.main(
            argv,
            prog="gurk run",
            description="Run a plugin.",
        )

    return e, capsys.readouterr()
