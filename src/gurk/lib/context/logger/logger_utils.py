from typing import IO

from rich import print as richprint

from gurk.lib.utils import typecheck

from .logger_types import LoggerEnum, LoggerSeverity


@typecheck
def filter_pydantic_wrapper(traceback_str: str) -> str:
    """
    Filter out Pydantic's internal wrapper from error messages to improve readability.

    :param traceback_str: The original traceback string
    :type traceback_str: str
    :return: The filtered traceback string
    :rtype: str
    """
    lines = traceback_str.splitlines()
    cleaned = []

    i = 0
    while i < len(lines):
        # look ahead for a line containing _typecheck
        if i + 1 < len(lines) and "_typecheck(" in lines[i + 1]:
            # skip until we see validate_python
            while (
                i < len(lines)
                and "self.__pydantic_validator__.validate_python("
                not in lines[i]
            ):
                i += 1

            # skip the validate_python line and the line after it (if any)
            i += 2
            continue

        cleaned.append(lines[i])
        i += 1

    return "\n".join(cleaned)


@typecheck
def _logcolor(severity: LoggerEnum) -> str:
    """
    Generate a rich-formatted color string for the given severity.

    :param severity: Severity level
    :type severity: LoggerEnum
    :return: The rich-formatted color string
    :rtype: str
    """
    return f"{'bold 'if severity.bold else ''}{'bright_'if severity.bright else ''}{severity.color}"


@typecheck
def logstart(severity: LoggerEnum) -> str:
    """
    Generate a rich-formatted severity tag for logging.

    :param severity: Severity level
    :type severity: LoggerEnum
    :return: The rich-formatted severity tag
    :rtype: str
    """
    color = _logcolor(severity)
    return f"[{color}][{severity.label}][/{color}]"


@typecheck
def logrichprint(
    severity: LoggerSeverity,
    message: str,
    file: IO[str] | None = None,
) -> None:
    """
    Print a rich-formatted log message with the specified severity.

    :param severity: Severity level
    :type severity: LoggerSeverity
    :param message: The message to print
    :type message: str
    :param file: The output file (stdout/stderr). If None, defaults to stdout.
    :type file: IO[str] | None
    """
    richprint(f"{logstart(severity)} {message}", file=file)
