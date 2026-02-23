import os
import shutil
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from types import GenericAlias
from typing import Any, TypeGuard, TypeVar, overload

from packaging.version import InvalidVersion, Version
from pydantic import TypeAdapter, ValidationError

from .type_check import typecheck
from .types import Comparison, ListOrTuple


@typecheck
def generate_random_path(
    suffix: str | None = None,
    prefix: str | None = None,
    create: bool = False,
) -> Path:
    """
    Generate a random temporary file if an extension is
    provided in the suffix, else a directory path.

    :param suffix: Suffix for the temporary file or directory
    :type suffix: str | None
    :param prefix: Prefix for the temporary file or directory
    :type prefix: str | None
    :param create: Whether to create the file or directory
    :type create: bool
    :return: Path to the temporary file or directory
    :rtype: Path
    """
    if suffix is not None and suffix.startswith("."):
        # File
        fd, path = mkstemp(suffix, prefix)
        os.close(fd)
        if not create:
            os.remove(path)
    else:
        # Directory
        path = mkdtemp(suffix, prefix)
        if not create:
            shutil.rmtree(path)

    return Path(path)


@typecheck
def check_version(version: str) -> bool:
    """
    Check if the given version string conforms to semantic versioning.

    :param version: The version string to check.
    :type version: str
    :return: True if valid, False otherwise.
    :rtype: bool
    """
    try:
        Version(version)
        return True
    except InvalidVersion:
        return False


@typecheck
def compare_versions(v1: str, v2: str) -> Comparison | None:
    """
    Compare two version strings using packaging.version.Version.

    :param v1: First version string
    :type v1: str
    :param v2: Second version string
    :type v2: str
    :returns: Comparison result (v1 wrt. v2) or None if either version is invalid
    :rtype: Comparison | None
    """
    if not (check_version(v1) and check_version(v2)):
        return None

    if Version(v1) < Version(v2):
        return Comparison.SMALLER
    elif Version(v1) == Version(v2):
        return Comparison.EQUAL
    elif Version(v1) > Version(v2):
        return Comparison.BIGGER
    else:
        return None


T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


@overload
def full_isinstance(value: Any, expected_type: type[T], /) -> TypeGuard[T]:
    ...


@overload
def full_isinstance(
    value: Any, expected_type: type[set[T]], /
) -> TypeGuard[set[T]]:
    ...


@overload
def full_isinstance(
    value: Any, expected_type: type[list[T]], /
) -> TypeGuard[list[T]]:
    ...


@overload
def full_isinstance(
    value: Any, expected_type: type[dict[K, V]], /
) -> TypeGuard[dict[K, V]]:
    ...


@overload
def full_isinstance(
    value: Any, expected_type: type[tuple[T, ...]], /
) -> TypeGuard[tuple[T, ...]]:
    ...


@typecheck
def full_isinstance(value: Any, expected_type: type | GenericAlias, /) -> bool:
    """
    Check if a value is an instance of the expected type.

    :param value: The value to check.
    :type value: Any
    :param expected_type: The expected type (can be a plain type, Union, TypedDict, etc.).
    :type expected_type: type | GenericAlias
    :return: True if the value matches the expected type, False otherwise.
    :rtype: bool
    """
    adapter = TypeAdapter(expected_type)
    try:
        adapter.validate_python(value, strict=True, extra="forbid")
    except ValidationError:
        return False
    else:
        return True


@typecheck
def overlay_dicts(dicts: ListOrTuple[dict]) -> dict:
    """
    Overlay multiple dictionaries in order, with later
    dictionaries replacing or updating keys in earlier ones.

    :param dicts: List of dictionaries to overlay
    :type dicts: ListOrTuple[dict]
    :return: The resulting overlaid dictionary
    :rtype: dict
    :raises ValueError: If any item in dicts is not a dictionary
    """

    def _overlay_two_dicts(base: dict, overlay: dict) -> dict:
        """
        Recursively overlay overlay-dict onto base-dict.
        Keys in overlay replace or update those in base.

        :param base: The base dictionary to overlay onto
        :type base: dict
        :param overlay: The overlay dictionary with updates
        :type overlay: dict
        :return: The resulting dictionary after overlay
        :rtype: dict
        """
        overlayed = deepcopy(base)
        for key, value in overlay.items():
            if (
                key in overlayed
                and isinstance(overlayed[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively overlay nested dicts
                overlayed[key] = _overlay_two_dicts(overlayed[key], value)
            else:
                # Directly set/replace value
                overlayed[key] = value
        return overlayed

    # Check input
    if not all(isinstance(d, dict) for d in dicts):
        raise ValueError(
            "Input 'dicts' must be a list of dictionaries, "
            f"got: {[type(d) for d in dicts]}"
        )

    # Overlay all dictionaries in order
    overlayed_dict = deepcopy(dicts[0])
    for current_dict in dicts[1:]:
        overlayed_dict = _overlay_two_dicts(overlayed_dict, current_dict)

    return overlayed_dict


def identity(x: T) -> T:
    """Return the input value unchanged."""
    return x


@typecheck
def get_timestamp(unique: bool = False) -> str:
    """
    Get a consistent, unique timestamp string, incrementing by a second
    if called multiple times within the same second and `unique` is True.

    :param unique: Whether to ensure uniqueness by incrementing if called multiple times within the same second
    :type unique: bool
    :return: Timestamp string in format YYYYMMDD_HHMMSS
    :rtype: str
    """
    curr_timestamp = datetime.now()
    last_timestamp = getattr(get_timestamp, "_last_timestamp", None)

    if unique and last_timestamp is not None:
        # Compare the formatted strings
        last_str = last_timestamp.strftime("%Y%m%d_%H%M%S")
        curr_str = curr_timestamp.strftime("%Y%m%d_%H%M%S")
        if curr_str <= last_str:
            # Increment by 1 second to ensure uniqueness
            curr_timestamp = last_timestamp + timedelta(seconds=1)

    # Save the current timestamp for next call
    setattr(get_timestamp, "_last_timestamp", curr_timestamp)

    return curr_timestamp.strftime("%Y%m%d_%H%M%S")


BASE_TIMESTAMP = get_timestamp()
