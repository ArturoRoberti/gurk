from dataclasses import dataclass, field
from typing import Any, Mapping, NotRequired, TypeAlias, TypedDict, Union

from gurk.utils.scripts import Command
from gurk.utils.yaml import overlay_dicts

FieldTypeDict: TypeAlias = Mapping[
    str, Union[list[type | None], "FieldTypeDict"]
]


def filled_properties(properties: FieldTypeDict) -> dict[str, Any]:
    """
    Given a FieldTypeDict, return a dict of default values for each property.

    :param properties: The FieldTypeDict to fill
    :type properties: FieldTypeDict
    :return: A dict with default values for each property
    :rtype: dict[str, Any]
    """
    result = {}
    for key, val in properties.items():
        if isinstance(val, dict):
            # Recurse into nested dict
            result[key] = filled_properties(val)
        else:
            # Use the first item as default, call it if callable
            default_value = val[0]
            result[key] = (
                default_value() if callable(default_value) else default_value
            )
    return result


# Required in default config
TASK_PROPERTIES_DEFAULT: FieldTypeDict = {
    "description": [str],
    "script": [str],
    "function": [None, str],
    "config_file": [None, str],
    "depends_on": [list],
    "privileged": [bool],
    "supercedes": [list],
    "args": {
        "allowed": [list],
        "default": [list],
    },
}
TASK_PROPERTIES_DEFAULT_FILLED = filled_properties(TASK_PROPERTIES_DEFAULT)

# Optional in custom config
TASK_PROPERTIES_CUSTOM: FieldTypeDict = {
    "enabled": [bool],
    "config_file": [None, str],  # TODO: Remove
    "args": [list],
}
TASK_PROPERTIES_CUSTOM_FILLED = filled_properties(TASK_PROPERTIES_CUSTOM)


# Explanations:
# - install-isaaclab: Hangs (may be an issue with the install itself, not the runner)
# - install-isaacsim: Takes too long (~30 mins); costs too much CI time - purely practical
# - install-nvidia-driver: Cannot use 'modprobe nvidia'
# - install-ros: Fails due to missing setup script (may be an issue with the install itself, not the runner)
RUNNER_SPECIFIC_TASKS = [
    "install-isaaclab",
    "install-isaacsim",
    "install-nvidia-driver",
    "install-ros",
]


def print_expected_task_fields(
    default: bool = False,
) -> str:
    """
    Returns a YAML-like string with a top-level task name, first-level
    properties and and second-level args, along with their expected types.

    :param default: Whether to use default task fields (True) or custom task fields (False)
    :type default: bool
    :return: Formatted string representing expected task fields
    :rtype: str
    """
    if default:
        keys_types = TASK_PROPERTIES_DEFAULT
    else:
        keys_types = TASK_PROPERTIES_CUSTOM

    def format_value(value):
        """Format a (non-dict) value into a single string."""
        if isinstance(value, (list, tuple, set)):
            formatted_items = []
            for v in value:
                if isinstance(v, type):
                    formatted_items.append(v.__name__)
                elif v is None:
                    formatted_items.append("null")
                else:
                    formatted_items.append(str(v))
            return ", ".join(formatted_items)
        elif isinstance(value, type):
            return value.__name__
        elif value is None:
            return "null"
        else:
            return str(value)

    entries = []  # list of (display_key, value)
    base_indent = " " * 2

    def walk(dct: dict, depth: int):
        """Depth-first traversal that appends (display_key, formatted_value|None)."""
        for key, val in dct.items():
            display_key = f"{base_indent * depth}{key}"
            if isinstance(val, dict):
                # header-only line, then recurse
                entries.append((display_key, ""))
                walk(val, depth + 1)
            else:
                entries.append((display_key, format_value(val)))

    # Walk nested dict
    walk(keys_types, depth=1)
    max_key_len = max(len(k) for k, _ in entries) + 2

    # Prepare final lines
    lines = ["<task-name>:"]
    for display_key, formatted_value in entries:
        spaces = " " * max(0, max_key_len - len(display_key))
        lines.append(f"{display_key}:{spaces}{formatted_value}")

    return "\n".join(lines)


def check_dict_structure(
    obj: Any, expected: FieldTypeDict, allow_default: bool = False
) -> bool:
    """
    Check if an object matches its expected structure (or is 'default').

    :param obj: The object to check
    :type obj: Any
    :param expected: Expected structure description
    :type expected: FieldTypeDict
    :param allow_default: Whether to allow 'default' as a valid value
    :type allow_default: bool
    :return: True if the object matches the expected structure, False otherwise
    :rtype: bool
    """
    if not isinstance(obj, dict):
        return False
    if set(obj.keys()) != set(expected.keys()):
        return False
    for expected_field, allowed_types in expected.items():
        # Nested dict
        if isinstance(allowed_types, dict):
            if not check_dict_structure(
                obj[expected_field], expected[expected_field], allow_default
            ):
                return False
            continue
        # 'None' value
        if obj[expected_field] is None and None in allowed_types:
            continue
        # 'default' value
        if obj[expected_field] == "default" and allow_default:
            continue
        # type value
        if type(obj[expected_field]) in allowed_types:
            continue
        return False
    return True


class DefaultTaskDict(TypedDict):
    """Dictionary representing a default task configuration."""

    # fmt: off
    description:    str
    script:         str
    function:       str | None
    config_file:    NotRequired[str | None]
    depends_on:     NotRequired[list[str]]
    privileged:     NotRequired[bool]
    supercedes:     NotRequired[list[str] | None]
    args:           NotRequired[dict[str, list[str]]]
    # fmt: on


class CustomTaskDict(TypedDict):
    """Dictionary representing a custom task configuration."""

    # fmt: off
    enabled:     bool
    config_file: NotRequired[str | None]
    args:        NotRequired[list[str]]
    # fmt: on


class TaskDict(DefaultTaskDict, CustomTaskDict):
    """Dictionary representing a full task configuration."""

    pass


DefaultTaskDictCollection: TypeAlias = dict[str, DefaultTaskDict]
CustomTaskDictCollection: TypeAlias = dict[str, CustomTaskDict]
TaskDictCollection: TypeAlias = dict[str, TaskDict]


def fill_missing_properties(
    tasks: dict[str, Any],
    default: bool,
) -> dict[str, Any]:
    """
    Given a task dictionary, fill in any missing properties with default values.

    :param task_dict: The task dictionary to fill
    :type task_dict: dict[str, Any]
    :param default: Whether to fill default task fields (True) or custom task fields (False)
    :type default: bool
    :return: The filled task dictionary
    :rtype: dict[str, Any]
    """
    if default:
        defaults_dict = TASK_PROPERTIES_DEFAULT_FILLED
    else:
        defaults_dict = TASK_PROPERTIES_CUSTOM_FILLED

    return {
        task_name: overlay_dicts([defaults_dict, task])
        for task_name, task in tasks.items()
    }


def get_invalid_tasks_from_task_dict_collection(
    obj: dict[Any, Any],
    default: bool,
) -> list[str] | None:
    """
    Check if an object is a valid collection of TaskDicts.
        NOTE: This allows empty dicts (no tasks) as valid input

    :param obj: The object to check
    :type obj: dict[Any, Any]
    :param default: Whether to check for default task fields (True) or custom task fields (False)
    :type default: bool
    :return: List of invalid task names, or None if the object is not a dict
    :rtype: list[str] | None
    """
    if not isinstance(obj, dict):
        return None

    return [
        key
        for key, value in obj.items()
        if not check_dict_structure(
            value,
            TASK_PROPERTIES_DEFAULT if default else TASK_PROPERTIES_CUSTOM,
            not default,
        )
    ]


@dataclass(frozen=True)
class ResolvedTask:
    """Represents a resolved task with its name, command, dependencies, and arguments."""

    # fmt: off
    name:        str           = field()
    command:     Command       = field()
    config_file: str | None    = field(default=None)
    depends_on:  tuple[str]    = field(default_factory=tuple)
    privileged:  bool          = field(default=False)
    args:        tuple[str]    = field(default_factory=tuple)
    # fmt: on
