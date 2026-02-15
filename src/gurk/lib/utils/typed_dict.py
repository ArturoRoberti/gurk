import types
from typing import (
    Any,
    Literal,
    NotRequired,
    TypeGuard,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
    overload,
)

from pydantic import TypeAdapter, ValidationError

from gurk.lib.utils.common import typecheck

#################################################################################################################
##################################################### Check #####################################################
#################################################################################################################
T = TypeVar("T")


@typecheck
def full_isinstance(value: Any, expected_type: type[T]) -> TypeGuard[T]:
    """
    Check if a value is an instance of the expected type.

    :param value: The value to check.
    :type value: Any
    :param expected_type: The expected type (can be a plain type, Union, TypedDict, etc.).
    :type expected_type: type[T]
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


#################################################################################################################
##################################################### Fill ######################################################
#################################################################################################################


def fill_typed_dict(data: Any, tp: type[T]) -> T:
    """
    Recursively fill a TypedDict (or nested structures containing TypedDicts) with default values.

    :param data: The data to fill (can be a dict or None).
    :type data: Any
    :param tp: The TypedDict type to use for filling.
    :type tp: type[T]
    :return: The filled data.
    :rtype: T
    """
    origin = get_origin(tp)
    args = get_args(tp)

    # unwrap NotRequired / Union
    if origin is NotRequired:
        return fill_typed_dict(data, args[0])
    if origin in (Union, types.UnionType):
        return fill_typed_dict(data, args[0])

    # TypedDict schema
    if is_typeddict(tp) and isinstance(data, dict):
        for key, sub_tp in get_type_hints(tp, include_extras=True).items():
            if key not in data:
                data[key] = fill_typed_dict(None, sub_tp)
            else:
                data[key] = fill_typed_dict(data[key], sub_tp)
        return data

    # dict[K, V]
    if origin is dict and isinstance(data, dict):
        val_tp = args[1]
        for k in data:
            data[k] = fill_typed_dict(data[k], val_tp)
        return data

    # default construction
    if data is None:
        if origin in (list, set, tuple, dict):
            return origin()
        if is_typeddict(tp):
            return fill_typed_dict({}, tp)
        return tp() if callable(tp) else None

    return data


#################################################################################################################
##################################################### Print #####################################################
#################################################################################################################


@overload
def print_typed_dict_types(
    td: Any,
    indent: int = ...,
    as_str: Literal[False] = ...,
) -> None:
    ...


@overload
def print_typed_dict_types(
    td: Any,
    indent: int = ...,
    as_str: Literal[True] = ...,
) -> str:
    ...


@typecheck
def print_typed_dict_types(
    td: Any, indent: int = 0, as_str: bool = False
) -> str | None:
    """
    Print the structure of a TypedDict type, including nested TypedDicts.

    :param td: The TypedDict type to print.
    :type td: Any
    :param indent: Number of spaces to use for indentation (default: 0).
    :type indent: int
    :param as_str: If True, return the output as a string instead of printing it.
    :type as_str: bool
    :return: The formatted string if `as_str` is True, otherwise None.
    :rtype: str | None
    """

    def type_to_str(tp: Any) -> str:
        """
        Convert a type annotation to a human-readable string.

        :param tp: The type annotation to convert.
        :type tp: Any
        :return: The human-readable string representation of the type.
        :rtype: str
        """
        if tp is None or tp is type(None):
            return "None"
        if isinstance(tp, type):
            return tp.__name__

        origin = get_origin(tp)
        args = get_args(tp)

        if origin in (list, set, tuple):
            return f"{origin.__name__}[{type_to_str(args[0])}]"
        if origin is dict and args:
            return f"dict[{type_to_str(args[0])}, {type_to_str(args[1])}]"
        if origin in (Union, types.UnionType):
            return " | ".join(type_to_str(a) for a in args)

        return str(tp)

    def contains_typeddict(tp: Any) -> bool:
        """
        Check if a type annotation contains a TypedDict (directly or nested).

        :param tp: The type annotation to check.
        :type tp: Any
        :return: True if the type annotation contains a TypedDict, otherwise False.
        :rtype: bool
        """
        if is_typeddict(tp):
            return True

        origin = get_origin(tp)
        args = get_args(tp)

        if origin is dict and args:
            return contains_typeddict(args[1])
        if origin in (list, set, tuple) and args:
            return contains_typeddict(args[0])
        if origin in (Union, types.UnionType):
            return any(contains_typeddict(a) for a in args)

        return False

    def render(tp: Any, key: str | None, ind: int) -> str:
        """
        Recursively render the structure of a TypedDict type as a formatted string.

        :param tp: The TypedDict type to render.
        :type tp: Any
        :param key: The key name for the current level (None for root).
        :type key: str | None
        :param ind: The indentation level.
        :type ind: int
        :return: The formatted string representation of the TypedDict structure.
        :rtype: str
        """
        prefix = " " * ind

        # Leaf (not TypedDict)
        if not is_typeddict(tp):
            if key is None:
                return prefix + type_to_str(tp) + "\n"
            return prefix + f"{key}: {type_to_str(tp)}\n"

        # TypedDict
        hints = get_type_hints(tp, include_extras=True)
        if not hints:
            return ""

        lines = []
        if key is not None:
            lines.append(prefix + key + ":\n")
            ind += 2
            prefix = " " * ind

        for name, ann in hints.items():
            is_nr = get_origin(ann) is NotRequired
            core = get_args(ann)[0] if is_nr else ann
            display = name + (" (NotRequired)" if is_nr else "")

            origin = get_origin(core)
            args = get_args(core)

            # Nested TypedDict
            if is_typeddict(core):
                lines.append(render(core, display, ind))

            # dict[K, V]
            elif origin is dict and args:
                ktype, vtype = args
                if contains_typeddict(vtype):
                    lines.append(prefix + display + ":\n")
                    lines.append(
                        " " * (ind + 2) + f"<{type_to_str(ktype)}>:\n"
                    )
                    lines.append(render(vtype, None, ind + 4))
                else:
                    lines.append(
                        prefix
                        + f"{display}: dict[{type_to_str(ktype)}, {type_to_str(vtype)}]\n"
                    )

            # list/set/tuple
            elif origin in (list, set, tuple) and args:
                elem = args[0]
                if contains_typeddict(elem):
                    lines.append(prefix + display + ":\n")
                    lines.append(" " * (ind + 2) + "-\n")
                    lines.append(render(elem, None, ind + 4))
                else:
                    lines.append(
                        prefix
                        + f"{display}: {origin.__name__}[{type_to_str(elem)}]\n"
                    )

            # Union
            elif origin in (Union, types.UnionType):
                parts = [
                    type_to_str(a) if not contains_typeddict(a) else "<...>"
                    for a in args
                ]
                lines.append(
                    prefix + f"{display}: " + " | ".join(parts) + "\n"
                )

            # Simple inline
            else:
                lines.append(prefix + f"{display}: {type_to_str(core)}\n")

        return "".join(lines)

    result = render(td, None, indent)

    if as_str:
        return result
    else:
        print(result)
        return
