import types
from typing import (
    Any,
    NotRequired,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)


#################################################################################################################
##################################################### Check #####################################################
#################################################################################################################
def _is_typed_dict(tp: Any) -> bool:
    """
    Check if a type is a TypedDict.

    :param tp: The type to check.
    :type tp: Any
    :return: True if the type is a TypedDict, False otherwise.
    :rtype: bool
    """
    return (
        isinstance(tp, type)
        and issubclass(tp, dict)
        and hasattr(tp, "__annotations__")
        and hasattr(tp, "__required_keys__")
    )


def is_instance_of_type(value: Any, expected_type: Any) -> bool:
    """
    Check if a value is an instance of the expected type.

    :param value: The value to check.
    :type value: Any
    :param expected_type: The expected type (can be a plain type, Union, TypedDict, etc.).
    :type expected_type: Any
    :return: True if the value matches the expected type, False otherwise.
    :rtype: bool
    """
    origin = get_origin(expected_type)
    args = get_args(expected_type)

    # Handle NotRequired
    if origin is NotRequired:
        # The field is optional; only validate type if value is present
        return is_instance_of_type(value, args[0])

    # TypedDict → recurse
    if _is_typed_dict(expected_type):
        return validate_typed_dict(value, expected_type)

    # Plain types (int, str, bool, etc.)
    if origin is None:
        return isinstance(value, expected_type)

    # Union / Optional
    if origin is Union or origin is types.UnionType:
        return any(is_instance_of_type(value, t) for t in args)

    # List / tuple / set
    if origin in (list, tuple, set):
        if not isinstance(value, origin):
            return False
        if not args:
            return True
        return all(is_instance_of_type(v, args[0]) for v in value)

    # Dict[K, V]
    if origin is dict:
        if not isinstance(value, dict):
            return False
        key_type, val_type = args
        return all(
            is_instance_of_type(k, key_type)
            and is_instance_of_type(v, val_type)
            for k, v in value.items()
        )

    return False


def _validate_typed_dict_keys(data: dict[str, Any], td_cls: dict) -> bool:
    """
    Validate that data has the correct keys for a TypedDict definition.

    :param data: The data dictionary to validate.
    :type data: dict[str, Any]
    :param td_cls: The TypedDict class defining the expected keys.
    :type td_cls: dict
    :return: True if the keys match the TypedDict definition, False otherwise.
    :rtype: bool
    """
    if not _is_typed_dict(td_cls) or not isinstance(data, dict):
        return False

    # Check required keys
    annotations = td_cls.__annotations__
    required_keys = {
        k
        for k, t in annotations.items()
        if not (get_origin(t) is NotRequired)
        and (
            td_cls.__total__
            or k in getattr(td_cls, "__required_keys__", annotations)
        )
    }
    allowed_keys = annotations.keys()
    if not (
        required_keys.issubset(data.keys())
        and set(data.keys()).issubset(allowed_keys)
    ):
        return False

    return True


def validate_typed_dict(data: Any, td_cls: dict) -> bool:
    """
    Validate that data matches a TypedDict definition.

    :param data: The data to validate.
    :type data: Any
    :param td_cls: The TypedDict class defining the expected structure.
    :type td_cls: dict
    :return: True if the data matches the TypedDict definition, False otherwise.
    :rtype: bool
    """
    if not _is_typed_dict(td_cls) or not isinstance(data, dict):
        return False

    # Check required keys
    if not _validate_typed_dict_keys(data, td_cls):
        return False

    # Check value types
    for key, expected_type in td_cls.__annotations__.items():
        if key in data and not is_instance_of_type(data[key], expected_type):
            return False

    return True


#################################################################################################################
##################################################### Fill ######################################################
#################################################################################################################
def _build_default(tp: Any) -> Any:
    """
    Build a default value for the given type annotation.

    :param tp: The type annotation.
    :type tp: Any
    :return: A default value for the type.
    :rtype: Any
    """
    origin = get_origin(tp)
    args = get_args(tp)

    # NotRequired[T]
    if origin is NotRequired:
        return _build_default(args[0])

    # TypedDict
    if _is_typed_dict(tp):
        return fill_typed_dict({}, tp)

    # Union / Optional
    if origin is Union or origin is types.UnionType:
        return _build_default(args[0])

    # list[T] | set[T] | tuple[T, ...] | dict[K, V]
    if origin in {list, set, tuple, dict}:
        return origin()

    # Plain type
    return tp() if callable(tp) else None


def fill_value(value: Any, annotated_type: Any) -> None:
    """
    Fill a value according to its annotated type.

    :param value: The value to fill.
    :type value: Any
    :param annotated_type: The annotated type to use for filling.
    :type annotated_type: Any
    """
    origin = get_origin(annotated_type)

    # unwrap NotRequired
    if origin is NotRequired:
        annotated_type = get_args(annotated_type)[0]
        origin = get_origin(annotated_type)

    # TypedDict
    if _is_typed_dict(annotated_type) and isinstance(value, dict):
        fill_typed_dict(value, annotated_type)
        return

    # dict[K, V]
    if origin is dict and isinstance(value, dict):
        _, val_type = get_args(annotated_type)
        for v in value.values():
            fill_value(v, val_type)


def fill_typed_dict(data: dict, td_type: dict) -> dict:
    """
    Treat TypedDict as a schema:
    - All fields are created if missing
    - Nested containers and TypedDicts are recursively materialized
    - Existing values are preserved
    """
    origin = get_origin(td_type)
    if origin is dict:
        # If this is a dict[K, V] schema, recurse into values
        _, val_type = get_args(td_type)
        for k, v in data.items():
            if v is None:
                data[k] = _build_default(val_type)
            fill_value(data[k], val_type)
        return data
    elif not _is_typed_dict(td_type):
        # Not a TypedDict schema, return as is
        return data

    hints = get_type_hints(td_type, include_extras=True)

    for key, annotated_type in hints.items():
        if key not in data:
            data[key] = _build_default(annotated_type)
        else:
            fill_value(data[key], annotated_type)

    return data


#################################################################################################################
##################################################### Print #####################################################
#################################################################################################################
def print_typed_dict_types(td: Any, indent: int = 0) -> None:
    """
    Print the types of a TypedDict's fields in a human-readable format.

    :param td: The TypedDict class to print.
    :type td: Any
    :param indent: Indentation level (number of spaces).
    :type indent: int
    """
    if not _is_typed_dict(td):
        print(" " * indent + _type_to_str(td))
        return

    hints = get_type_hints(td, include_extras=True)
    if not hints:
        return

    # Prepare fields and compute padding only for inline fields
    fields = []
    max_inline = 0
    for k, ann in hints.items():
        is_nr = get_origin(ann) is NotRequired
        core = get_args(ann)[0] if is_nr else ann
        display = k + (" (NotRequired)" if is_nr else "")
        inline = _is_inline_type(core)
        fields.append((display, core, inline))
        if inline:
            max_inline = max(max_inline, len(display))

    for display, tp, inline in fields:
        key = display.ljust(max_inline) if inline else display
        _print_field(key, tp, indent)


def _print_field(key: str, tp: Any, indent: int) -> None:
    """
    Print a single field of a TypedDict, handling nested TypedDicts and containers.

    :param key: Field name to print
    :type key: str
    :param tp: Type of the field
    :type tp: Any
    :param indent: Indentation level (number of spaces)
    :type indent: int
    """
    origin = get_origin(tp)

    # TypedDict -> newline then recurse
    if _is_typed_dict(tp):
        print(" " * indent + key + ":")
        print_typed_dict_types(tp, indent + 2)
        return

    # dict[K, V] where V contains TypedDict -> print <K>: then recurse into V
    if origin is dict and (args := get_args(tp)):
        ktype, vtype = args
        if _container_has_typed_dict(vtype):
            print(" " * indent + key + ":")
            print(" " * (indent + 2) + f"<{_type_name(ktype)}>:")
            _print_container_as_fields(vtype, indent + 4)
            return
        # plain dict printed inline
        print(
            " " * indent
            + key
            + f": dict[{_type_to_str(ktype)}, {_type_to_str(vtype)}]"
        )
        return

    # list/set/tuple containing TypedDict -> print key then recurse into element
    if (
        origin in (list, set, tuple)
        and (args := get_args(tp))
        and _container_has_typed_dict(args[0])
    ):
        print(" " * indent + key + ":")
        print(" " * (indent + 2) + "-")
        _print_container_as_fields(args[0], indent + 4)
        return

    # Union (PEP 604 or typing.Union)
    if origin in (Union, types.UnionType):
        parts = []
        for a in get_args(tp):
            parts.append(
                _type_to_str(a)
                if not _container_has_typed_dict(a)
                else "<...>"
            )
        print(" " * indent + key + ": " + " | ".join(parts))
        return

    # fallback: simple inline type
    print(" " * indent + key + ": " + _type_to_str(tp))


def _print_container_as_fields(tp: Any, indent: int) -> None:
    """
    Print the contents of a container type (dict, list, set, tuple) as fields.

    :param tp: Type of the container
    :type tp: Any
    :param indent: Indentation level (number of spaces)
    :type indent: int
    """
    if _is_typed_dict(tp):
        print_typed_dict_types(tp, indent)
        return
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is dict and args:
        print(" " * indent + f"<{_type_name(args[0])}>:")
        _print_container_as_fields(args[1], indent + 2)
    elif origin in (list, set, tuple) and args:
        _print_container_as_fields(args[0], indent)
    else:
        print(" " * indent + _type_to_str(tp))


def _container_has_typed_dict(tp: Any) -> bool:
    """
    Return True if this type is or contains a TypedDict.

    :param tp: The type to check
    :type tp: Any
    :return: True if the type is or contains a TypedDict, False otherwise
    :rtype: bool
    """
    if _is_typed_dict(tp):
        return True
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is dict and args:
        return _container_has_typed_dict(args[1])
    if origin in (list, set, tuple) and args:
        return _container_has_typed_dict(args[0])
    return False


def _type_name(tp: Any) -> str:
    """
    Get the name of a type.

    :param tp: The type to get the name of
    :type tp: Any
    :return: The name of the type
    :rtype: str
    """
    return getattr(tp, "__name__", str(tp))


def _type_to_str(tp: Any) -> str:
    """
    Convert a type annotation to a human-readable string.

    :param tp: The type to convert to a string
    :type tp: Any
    :return: A human-readable string representation of the type
    :rtype: str
    """
    if tp is None or tp is type(None):
        return "None"
    if isinstance(tp, type):
        return tp.__name__
    origin = get_origin(tp)
    args = get_args(tp)
    if origin in (list, set, tuple):
        inner = _type_to_str(args[0]) if args else ""
        return f"{origin.__name__}[{inner}]"
    if origin is dict and args:
        return f"dict[{_type_to_str(args[0])}, {_type_to_str(args[1])}]"
    if origin in (Union, types.UnionType):
        return " | ".join(_type_to_str(a) for a in args)
    return str(tp)


def _is_inline_type(tp: Any) -> bool:
    """
    Determine if a type should be printed inline.

    :param tp: The type to check
    :type tp: Any
    :return: True if the type should be printed inline, False otherwise
    :rtype: bool
    """
    if _is_typed_dict(tp):
        return False
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is dict and args:
        return not _container_has_typed_dict(args[1])
    if origin in (list, set, tuple) and args:
        return not _container_has_typed_dict(args[0])
    if origin in (Union, type(Union)):
        # inline if none of the union types are TypedDicts
        return all(not _container_has_typed_dict(a) for a in args)
    return True
