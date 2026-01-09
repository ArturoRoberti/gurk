# TODO: Clean up, and maybe get some util from tasks in here. Try to restructure FieldTypeDict to use TypedDicts. How to incorporate allow_default?
# TODO: Have central "validator" class?

import types
from typing import Any, NotRequired, TypedDict, Union, get_args, get_origin


def _is_typed_dict_type(tp: Any) -> bool:
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
    if _is_typed_dict_type(expected_type):
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


def validate_typed_dict_keys(
    data: dict[str, Any], td_cls: type[TypedDict]
) -> bool:
    """
    Validate that data has the correct keys for a TypedDict definition.

    :param data: The data dictionary to validate.
    :type data: dict[str, Any]
    :param td_cls: The TypedDict class defining the expected keys.
    :type td_cls: type[TypedDict]
    :return: True if the keys match the TypedDict definition, False otherwise.
    :rtype: bool
    """
    if not isinstance(data, dict):
        return False
    elif not all(isinstance(k, str) for k in data.keys()):
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
        or set(data.keys()).issubset(allowed_keys)
    ):
        return False

    return True


def validate_typed_dict(data: Any, td_cls: type[TypedDict]) -> bool:
    """
    Validate that data matches a TypedDict definition.

    :param data: The data to validate.
    :type data: Any
    :param td_cls: The TypedDict class defining the expected structure.
    :type td_cls: type[TypedDict]
    :return: True if the data matches the TypedDict definition, False otherwise.
    :rtype: bool
    """
    if not isinstance(data, dict):
        return False
    elif not all(isinstance(k, str) for k in data.keys()):
        return False

    # Check required keys
    if not validate_typed_dict_keys(data, td_cls):
        return False

    # Check value types
    for key, expected_type in td_cls.__annotations__.items():
        if key in data and not is_instance_of_type(data[key], expected_type):
            return False

    return True
