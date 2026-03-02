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

import json
import os
from functools import cache, wraps
from importlib.metadata import Distribution
from types import GenericAlias
from typing import Any, Literal, TypeGuard, TypeVar, overload

from pydantic import ConfigDict, TypeAdapter, ValidationError, validate_call

from .constants import NO_ANSWERS, PACKAGE_NAME, YES_ANSWERS


@cache
def _is_typecheck_active() -> bool:
    # (Priority) Check environment variable override
    gurk_typecheck = os.getenv("GURK_TYPECHECK")
    if gurk_typecheck in YES_ANSWERS:
        return True
    elif gurk_typecheck in NO_ANSWERS:
        return False
    else:
        # See if the package is installed in editable mode
        direct_url = Distribution.from_name(PACKAGE_NAME).read_text(
            "direct_url.json"
        )
        return (
            json.loads(direct_url).get("dir_info", {}).get("editable", False)
        )


class InputValidationError(Exception):
    """Custom error type for input validation errors in typecheck."""

    pass


def typecheck(
    _func=None,
    /,
    *,
    strict: bool = True,
    extra: Literal["forbid", "allow", "ignore"] = "forbid",
):
    """
    Decorator (or decorator factory) that wraps a function with runtime type checking.

    Can be used as:
      @typecheck                               uses defaults
      @typecheck(strict=False, extra="allow")  custom settings

    :param strict: Whether to enforce strict type checking (e.g., disallowing extra fields in TypedDicts)
    :type strict: bool
    :param extra: How to handle extra fields in TypedDicts ("forbid", "allow", "ignore")
    :type extra: Literal["forbid", "allow", "ignore"]
    :raises InputValidationError: If the input validation fails, with details on the offending inputs
    """

    def decorator(func):
        if not _is_typecheck_active():
            return func

        checked_func = validate_call(
            config=ConfigDict(
                strict=strict, extra=extra, arbitrary_types_allowed=True
            )
        )(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return checked_func(*args, **kwargs)
            except ValidationError as e:
                messages = []
                for err in e.errors():
                    loc = ".".join(str(x) for x in err["loc"])
                    bad_input = err.get("input", "<missing>")
                    bad_type = type(bad_input).__name__
                    bad_repr = repr(bad_input)
                    if len(bad_repr) > 200:
                        bad_repr = bad_repr[:197] + "..."
                    messages.append(
                        f"{loc}: {err['msg']} (got {bad_type}: {bad_repr})"
                    )
                raise InputValidationError(
                    "Wrong input(s) to '"
                    + func.__name__
                    + "':\n"
                    + "\n".join(messages)
                ) from None

        return wrapper

    if _func is not None:
        return decorator(_func)
    return decorator


T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


@overload
def full_isinstance(
    value: Any,
    expected_type: type[T],
    /,
    *,
    strict: bool = ...,
    extra: str = ...,
) -> TypeGuard[T]:
    ...


@overload
def full_isinstance(
    value: Any,
    expected_type: type[set[T]],
    /,
    *,
    strict: bool = ...,
    extra: str = ...,
) -> TypeGuard[set[T]]:
    ...


@overload
def full_isinstance(
    value: Any,
    expected_type: type[list[T]],
    /,
    *,
    strict: bool = ...,
    extra: str = ...,
) -> TypeGuard[list[T]]:
    ...


@overload
def full_isinstance(
    value: Any,
    expected_type: type[dict[K, V]],
    /,
    *,
    strict: bool = ...,
    extra: str = ...,
) -> TypeGuard[dict[K, V]]:
    ...


@overload
def full_isinstance(
    value: Any,
    expected_type: type[tuple[T, ...]],
    /,
    *,
    strict: bool = ...,
    extra: str = ...,
) -> TypeGuard[tuple[T, ...]]:
    ...


@typecheck
def full_isinstance(
    value: Any,
    expected_type: type | GenericAlias,
    /,
    *,
    strict: bool = True,
    extra: str = "forbid",
) -> bool:
    """
    Check if a value is an instance of the expected type.

    :param value: The value to check.
    :type value: Any
    :param expected_type: The expected type (can be a plain type, Union, TypedDict, etc.).
    :type expected_type: type | GenericAlias
    :param strict: Whether to enforce strict type checking (e.g., disallowing extra fields in TypedDicts)
    :type strict: bool
    :param extra: How to handle extra fields in TypedDicts ("forbid", "allow", "ignore")
    :type extra: str
    :return: True if the value matches the expected type, False otherwise.
    :rtype: bool
    """
    adapter = TypeAdapter(expected_type)
    try:
        adapter.validate_python(value, strict=strict, extra=extra)
    except ValidationError:
        return False
    else:
        return True
