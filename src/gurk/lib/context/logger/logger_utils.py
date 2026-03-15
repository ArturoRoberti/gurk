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

import inspect
from io import TextIOBase
from typing import Literal, overload

from rich.markup import escape

from gurk.lib.shared.printers import richprint
from gurk.lib.utils import PatternCollection, typecheck

from .logger_types import LoggerSeverity


@typecheck
def _filter_pydantic_wrapper(traceback_str: str) -> str:
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
        m = PatternCollection.TRACEBACK_FILE.patterns.match(lines[i])
        if m and m.group(1) == inspect.getfile(typecheck):
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


@overload
def logrichprint(
    severity: LoggerSeverity,
    message: str,
    as_str: Literal[False] = ...,
    file: TextIOBase | None = ...,
) -> None: ...


@overload
def logrichprint(
    severity: LoggerSeverity,
    message: str,
    as_str: Literal[True] = ...,
    file: TextIOBase | None = ...,
) -> str: ...


@typecheck
def logrichprint(
    severity: LoggerSeverity,
    message: str,
    as_str: bool = False,
    file: TextIOBase | None = None,
) -> str | None:
    """
    Print a rich-formatted log message with the specified severity.

    :param severity: Severity level
    :type severity: LoggerSeverity
    :param message: The message to print
    :type message: str
    :param as_str: If True, return the formatted message as a string instead of printing it
    :type as_str: bool
    :param file: The output file (stdout/stderr). If None, defaults to stdout.
    :type file: TextIOBase | None
    :return: The formatted message if as_str is True, otherwise None
    :rtype: str | None
    """
    color = f"{'bold 'if severity.bold else ''}{'bright_'if severity.bright else ''}{severity.color}"
    msg = f"{richprint(escape(f'[{severity.label}]'), color=color, as_str=True)} {message}"
    if as_str:
        return msg
    else:
        richprint(msg, file=file)
