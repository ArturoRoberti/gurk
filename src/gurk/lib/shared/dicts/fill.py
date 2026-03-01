import types
from typing import (
    NotRequired,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

T = TypeVar("T")


def fill_typed_dict(dct: dict, tp: type[T]) -> T:
    """
    Recursively fill a TypedDict (or nested structures containing TypedDicts) with default values.
        :NOTE: This function recursively calls itself with different input types, so it is not strictly type-safe.

    :param dct: The dict to fill.
    :type dct: dict
    :param tp: The TypedDict type to use for filling.
    :type tp: type[T]
    :return: The filled dict.
    :rtype: T
    """
    origin = get_origin(tp)
    args = get_args(tp)

    # unwrap NotRequired / Union
    if origin is NotRequired:
        return fill_typed_dict(dct, args[0])
    if origin in (Union, types.UnionType):
        return fill_typed_dict(dct, args[0])

    # TypedDict schema
    if is_typeddict(tp) and isinstance(dct, dict):
        for key, sub_tp in get_type_hints(tp, include_extras=True).items():
            if key not in dct:
                dct[key] = fill_typed_dict(None, sub_tp)
            else:
                dct[key] = fill_typed_dict(dct[key], sub_tp)
        return dct

    # dict[K, V]
    if origin is dict and isinstance(dct, dict):
        val_tp = args[1]
        for k in dct:
            dct[k] = fill_typed_dict(dct[k], val_tp)
        return dct

    # default construction
    if dct is None:
        if origin in (list, set, tuple, dict):
            return origin()
        if is_typeddict(tp):
            return fill_typed_dict({}, tp)
        return tp() if callable(tp) else None

    return dct
