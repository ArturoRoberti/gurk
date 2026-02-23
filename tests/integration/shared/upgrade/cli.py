import pytest
from _pytest._code.code import ExceptionInfo
from _pytest.capture import CaptureFixture, CaptureResult

from gurk.cli import upgrade


def gurk_upgrade(
    argv: list[str], capsys: CaptureFixture[str]
) -> tuple[ExceptionInfo[SystemExit], CaptureResult[str]]:
    """
    Helper function to execute the 'gurk upgrade' command and capture its output.

    :param argv: List of command-line arguments to pass to 'gurk upgrade'.
    :type argv: list[str]
    :param capsys: Pytest fixture to capture stdout and stderr.
    :type capsys: CaptureFixture[str]
    :return: A tuple containing the exception info and captured output.
    :rtype: tuple[ExceptionInfo[SystemExit], CaptureResult[str]]
    """
    with pytest.raises(SystemExit) as e:
        upgrade.main(
            argv,
            prog="gurk upgrade",
            description="Remove a plugin from the registry.",
        )

    return e, capsys.readouterr()
