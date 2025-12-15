from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union

from cmstp.utils.command import Command

FieldTypeDict = Dict[str, List[Optional[type]]]

# Required in default config - "'script': None" is actually not allowed, but defaults to None if nonexistent package is used
TASK_ARGS_DEFAULT: FieldTypeDict = {
    "allowed": [list, None],
    "default": [list],
}
TASK_PROPERTIES_DEFAULT: FieldTypeDict = {
    "description": [str],  # TODO: Use and add pytest
    "script": [str],
    "function": [None, str],
    "config_file": [None, str],  # TODO: Use and add pytest
    "depends_on": [list],
    "privileged": [bool],
    "supercedes": [None, list],  # TODO: Use and add pytest
}

# Optional in custom config
TASK_PROPERTIES_CUSTOM: FieldTypeDict = {
    "enabled": [bool],
    "config_file": [None, str],  # TODO: Use and add pytest
    "args": [list],
}

# TODO: Auto-detect via flag in default config?
HARDWARE_SPECIFIC_TASKS = ["install-nvidia-driver", "install-cuda"]


def print_expected_task_fields(
    keys_types: FieldTypeDict, args_types: Optional[FieldTypeDict] = None
) -> str:
    """
    Returns a YAML-like string with a top-level task name, first-level
    properties and and second-level args, along with their expected types.

    :param args_types: Types for args fields
    :type args_types: FieldTypeDict
    :param keys_types: Types for top-level task fields
    :type keys_types: FieldTypeDict
    :return: Formatted string representing expected task fields
    :rtype: str
    """

    def format_value(value):
        formatted_items = []
        for v in value:
            if isinstance(v, type):
                formatted = v.__name__
            elif v is None:
                formatted = "null"
            else:
                formatted = str(v)
            formatted_items.append(formatted)

        return ", ".join(formatted_items)

    # Prepare key width for alignment (including indented args keys)
    all_keys = list(keys_types.keys())
    if args_types:
        all_keys += [f"  {k}" for k in args_types.keys()]
    max_key_len = max(len(k) for k in all_keys) + 2

    lines = ["<task-name>:"]
    indent = "  "  # base indent for content under task

    # Add top-level keys
    for key, value in keys_types.items():
        lines.append(
            f"{indent}{key}:{' ' * (max_key_len - len(key))}{format_value(value)}"
        )

    # Add args section
    if args_types:
        lines.append(f"{indent}args:")
        for key, value in args_types.items():
            indented_key = f"{indent}  {key}"
            lines.append(
                f"{indented_key}:{' ' * (max_key_len - len(f'  {key}'))}{format_value(value)}"
            )

    return "\n".join(lines)


def check_structure(obj: Any, expected: FieldTypeDict) -> bool:
    """
    Check if an object matches its expected structure.

    :param obj: The object to check
    :type obj: Any
    :param expected: Expected structure description
    :type expected: FieldTypeDict
    :return: True if the object matches the expected structure, False otherwise
    :rtype: bool
    """
    if not isinstance(obj, dict):
        return False
    if set(obj.keys()) != set(expected.keys()):
        return False
    for key, types in expected.items():
        if None in types and obj[key] is None:
            continue
        if type(obj[key]) not in types:
            return False
    return True


class ArgsDict(TypedDict):
    """Dictionary representing task arguments in the default config file."""

    # fmt: off
    allowed:          Optional[List[str]]
    default:          List[str]
    # fmt: on


def is_args_dict(
    obj: Any, include_default: bool = True, include_custom: bool = False
) -> bool:
    """
    Check if an object is a valid ArgsDict

    :param obj: The object to check
    :type obj: Any
    :param include_default: Whether to include default args in the check
    :type include_default: bool
    :param include_custom: Whether to include custom args in the check
    :type include_custom: bool
    :return: True if the object is a valid ArgsDict, False otherwise
    :rtype: bool
    """
    if include_custom:
        return isinstance(obj, list) and all(
            isinstance(arg, str) for arg in obj
        )
    else:
        expected_args = dict()
        if include_default:
            expected_args |= TASK_ARGS_DEFAULT

        return check_structure(obj, expected_args)


class TaskDict(TypedDict):
    """Dictionary representing a task configuration."""

    # fmt: off
    enabled:        bool
    description:    str
    script:         str
    function:       Optional[str]
    config_file:    Optional[str]
    depends_on:     List[str]
    privileged:     bool
    supercedes:     Optional[List[str]]
    args:           Union[ArgsDict, List[str]]
    # fmt: on


def is_task_dict(
    obj: Any, include_default: bool = True, include_custom: bool = False
) -> bool:
    """
    Check if an object is a valid TaskDict.

    :param obj: The object to check
    :type obj: Any
    :param include_default: Whether to include default properties in the check
    :type include_default: bool
    :param include_custom: Whether to include custom properties in the check
    :type include_custom: bool
    :return: True if the object is a valid TaskDict, False otherwise
    :rtype: bool
    """
    expected_keys = dict()
    if include_default:
        expected_keys |= TASK_PROPERTIES_DEFAULT
    if include_custom:
        expected_keys |= TASK_PROPERTIES_CUSTOM

    if not isinstance(obj, dict):
        return False

    if not include_custom:
        obj_noargs = {k: v for k, v in obj.items() if k != "args"}
        obj_args = obj.get("args")
        return check_structure(obj_noargs, expected_keys) and is_args_dict(
            obj_args,
            include_default=include_default,
            include_custom=include_custom,
        )
    else:
        return check_structure(obj, expected_keys)


TaskDictCollection = Dict[str, TaskDict]


def get_invalid_tasks_from_task_dict_collection(
    obj: Dict[Any, Any],
    include_default: bool = True,
    include_custom: bool = False,
) -> Optional[List[str]]:
    """
    Check if an object is a valid collection of TaskDicts.
        NOTE: This allows empty dicts (no tasks) as valid input

    :param obj: The object to check
    :type obj: Dict[Any, Any]
    :param include_default: Whether to include default properties in the check
    :type include_default: bool
    :param include_custom: Whether to include custom properties in the check
    :type include_custom: bool
    :return: List of invalid task names, or None if the object is not a dict
    :rtype: List[str] | None
    """
    if not isinstance(obj, dict):
        return None

    invalid_tasks = []
    for key, value in obj.items():
        if not isinstance(key, str) or not is_task_dict(
            value,
            include_default=include_default,
            include_custom=include_custom,
        ):
            invalid_tasks.append(key)
    return invalid_tasks


@dataclass(frozen=True)
class ResolvedTask:
    """Represents a resolved task with its name, command, dependencies, and arguments."""

    # fmt: off
    name:        str           = field()
    command:     Command       = field()
    config_file: Optional[str] = field(default=None)
    depends_on:  Tuple[str]    = field(default_factory=tuple)
    privileged:  bool          = field(default=False)
    args:        Tuple[str]    = field(default_factory=tuple)
    # fmt: on
