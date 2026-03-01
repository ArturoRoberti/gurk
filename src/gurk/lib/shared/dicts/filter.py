from typing import TypeVar

from pydantic import TypeAdapter

from gurk.lib.utils import typecheck

T = TypeVar("T")


@typecheck
def filter_typed_dict(dct: dict, tp: type[T]) -> T:
    """
    Filter a dictionary to only include keys that are defined in the TypedDict.
        :NOTE: The input dict must still define all required keys of the TypedDict.

    :param dct: The dictionary to filter.
    :type dct: dict
    :param tp: The TypedDict type to use as the schema.
    :type tp: type[T]
    :return: The filtered dictionary.
    :rtype: T
    :raises ValidationError: If the input dictionary does not conform to the TypedDict schema.
    """
    return TypeAdapter(tp).validate_python(dct, extra="ignore")
