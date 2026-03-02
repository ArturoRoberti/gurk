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

from typing import Literal, TypeVar, overload

from rich import print as richprint

from gurk.lib.utils import typecheck

from ._pprint_dict import _render_dict_structure
from ._pprint_typed_dict import _render_typed_dict_structure


@overload
def pprint_dict(
    dct: dict,
    *,
    color: str = ...,
    capitalize: bool = ...,
    indent: int = ...,
    indent_step: int = ...,
    as_str: Literal[False] = ...,
) -> None: ...


@overload
def pprint_dict(
    dct: dict,
    *,
    color: str = ...,
    capitalize: bool = ...,
    indent: int = ...,
    indent_step: int = ...,
    as_str: Literal[True] = ...,
) -> str: ...


@typecheck
def pprint_dict(
    dct: dict,
    *,
    color: str = "white",
    capitalize: bool = False,
    indent: int = 0,
    indent_step: int = 2,
    as_str: bool = False,
) -> str | None:
    """
    Pretty-print a dictionary with rich text formatting.

    Renders a dictionary structure with aligned key:value pairs, optional key
    capitalization, and configurable indentation.

    :param dct: Dictionary to print
    :type dct: dict
    :param color: Rich color name for keys
    :type color: str
    :param capitalize: Capitalize string keys
    :type capitalize: bool
    :param indent: Starting indentation in spaces
    :type indent: int
    :param indent_step: Indentation per nesting level
    :type indent_step: int
    :param as_str: Return as string instead of printing
    :type as_str: bool
    :return: Formatted string if as_str is True, otherwise None
    :rtype: str | None
    """
    result = _render_dict_structure(
        dct,
        color=color,
        capitalize=capitalize,
        indent=indent,
        indent_step=indent_step,
    )
    if as_str:
        return result
    else:
        richprint(result)


T = TypeVar("T")


@overload
def pprint_typed_dict(
    td: type[T],
    *,
    color: str = ...,
    indent: int = ...,
    indent_step: int = ...,
    as_str: Literal[False] = ...,
) -> None: ...


@overload
def pprint_typed_dict(
    td: type[T],
    *,
    color: str = ...,
    indent: int = ...,
    indent_step: int = ...,
    as_str: Literal[True] = ...,
) -> str: ...


def pprint_typed_dict(
    td: type[T],
    *,
    color: str = "cyan",
    indent: int = 0,
    indent_step: int = 2,
    as_str: bool = False,
) -> str | None:
    """
    Pretty-print TypedDict or generic type structure with type annotations.

    Renders the structure of a TypedDict type including nested TypedDicts,
    generic types, and type hints with support for NotRequired fields.

    :param td: TypedDict type or generic type to print
    :type td: type[T]
    :param color: Rich color name for field tags
    :type color: str
    :param indent: Starting indentation in spaces
    :type indent: int
    :param indent_step: Indentation per nesting level
    :type indent_step: int
    :param as_str: Return as string instead of printing
    :type as_str: bool
    :return: Formatted string if as_str is True, otherwise None
    :rtype: str | None
    """
    result = _render_typed_dict_structure(
        td, color=color, indent=indent, indent_step=indent_step
    )
    if as_str:
        return result
    else:
        richprint(result)
