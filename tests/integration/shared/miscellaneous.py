from _pytest._code.code import ExceptionInfo
from _pytest.capture import CaptureResult

from ..utils import ExpectedOutcome


def assert_outcome(
    exception_info: ExceptionInfo[SystemExit],
    captured: CaptureResult[str],
    expected: ExpectedOutcome,
) -> None:
    """
    Assert that the outcome of the operation matches the expected outcome (success or failure) based on the captured exception information and output.

    :param exception_info: The exception information captured from the SystemExit exception.
    :type exception_info: ExceptionInfo[SystemExit]
    :param captured: The captured output from the operation.
    :type captured: CaptureResult[str]
    :param expected: The expected outcome of the operation.
    :type expected: ExpectedOutcome
    """

    def assertion_error(msg: str) -> str:
        def _captured_to_str(channel: str) -> str:
            return ("\n" + channel) if channel.strip() else " (Empty)"

        return (
            f"{msg}\n"
            f"stdout:{_captured_to_str(captured.out)}"
            f"stderr:{_captured_to_str(captured.err)}"
        )

    assert exception_info.value.code == expected.exit_code, assertion_error(
        f"Expected exit code {expected.exit_code}, but got {exception_info.value.code}"
    )
    assert (captured.err.strip() == "") == (
        not expected.contains_errors
    ), assertion_error(
        f"Expected {'' if expected.contains_errors else 'no '}stderr output."
    )
