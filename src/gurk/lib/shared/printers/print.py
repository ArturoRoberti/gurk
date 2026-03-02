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

from io import TextIOBase
from typing import Literal, overload

from rich import print as _richprint

from gurk.lib.utils import typecheck


@typecheck
def newline(*, file: TextIOBase | None = None) -> None:
    """
    Print a newline to the console output.

    :param file: The output file (stdout/stderr). If None, defaults to stdout.
    :type file: TextIOBase | None
    """
    print("", file=file)


@overload
def richprint(
    message: str,
    color: str | None = ...,
    as_str: Literal[False] = ...,
    file: TextIOBase | None = ...,
) -> None: ...


@overload
def richprint(
    message: str,
    color: str | None = ...,
    as_str: Literal[True] = ...,
    file: TextIOBase | None = ...,
) -> str: ...


@typecheck
def richprint(
    message: str,
    color: str | None = None,
    as_str: bool = False,
    file: TextIOBase | None = None,
) -> str | None:
    """
    Print a rich-formatted message with optional color.

    :param message: The message to print
    :type message: str
    :param color: Optional color for the message. If None, defaults to no additional color wrapping.
    :type color: str | None
    :param as_str: If True, return the formatted message as a string instead of printing it
    :type as_str: bool
    :param file: The output file (stdout/stderr). If None, defaults to stdout.
    :type file: TextIOBase | None
    :return: The formatted message if as_str is True, otherwise None
    :rtype: str | None
    """
    if color is not None:
        msg = f"[{color}]{message}[/{color}]"
    else:
        msg = message

    if as_str:
        return msg
    else:
        _richprint(msg, file=file)


@overload
def padded_print(
    text: str,
    color: str = ...,
    total_length: int = ...,
    top: bool = ...,
    bottom: bool = ...,
    as_str: Literal[False] = ...,
    file: TextIOBase | None = ...,
) -> None: ...


@overload
def padded_print(
    text: str,
    color: str = ...,
    total_length: int = ...,
    top: bool = ...,
    bottom: bool = ...,
    as_str: Literal[True] = ...,
    file: TextIOBase | None = ...,
) -> str: ...


@typecheck
def padded_print(
    text: str,
    color: str = "white",
    total_length: int = 128,
    top: bool = True,
    bottom: bool = True,
    as_str: bool = False,
    file: TextIOBase | None = None,
) -> str | None:
    """
    Print text padded with "=" signs to center it within a specified total length.

    :param text: Text to be printed
    :type text: str
    :param color: Color of the text
    :type color: str
    :param total_length: Total length of the printed line including padding
    :type total_length: int
    :param top: Whether to print the top padding line
    :type top: bool
    :param bottom: Whether to print the bottom padding line
    :type bottom: bool
    :param as_str: If True, return the formatted message as a string instead of printing it
    :type as_str: bool
    :param file: The output file (stdout/stderr). If None, defaults to stdout.
    :type file: TextIOBase | None
    :return: The formatted message if as_str is True, otherwise None
    :rtype: str | None
    """
    msg = ""

    # Top bar
    if top:
        msg += (
            richprint("=" * total_length, color=color, file=file, as_str=True)
            + "\n"
        )

    # Calculate how many "=" signs are needed in the middle
    #   Subtract 2 for extra spaces
    remaining_length = total_length - len(text) - 2
    if remaining_length < 0:
        msg += richprint(f"{text}", color=color, file=file, as_str=True)
    else:
        left_pad = remaining_length // 2
        right_pad = remaining_length - left_pad
        msg += richprint(
            f"{'=' * left_pad} {text} {'=' * right_pad}",
            color=color,
            file=file,
            as_str=True,
        )
    # Bottom bar
    if bottom:
        msg += "\n" + richprint(
            "=" * total_length, color=color, file=file, as_str=True
        )

    if as_str:
        return msg
    else:
        _richprint(msg, file=file)
