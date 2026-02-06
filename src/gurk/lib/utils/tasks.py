from dataclasses import dataclass, field
from pathlib import Path
from typing import NotRequired, TypeAlias, TypedDict, Union, get_type_hints

from gurk.lib.utils.scripts import Command

# Explanations:
# - nvidia/install-isaaclab: Hangs (may be an issue with the install itself, not the runner)
# - nvidia/install-isaacsim: Takes too long (~30 mins); costs too much CI time - purely practical
# - nvidia/install-nvidia-driver: Cannot use 'modprobe nvidia'
# - ros/install-ros: Fails due to missing setup script (may be an issue with the install itself, not the runner)
RUNNER_SPECIFIC_TASKS = [
    "nvidia/install-isaaclab",
    "nvidia/install-isaacsim",
    "nvidia/install-nvidia-driver",
    "ros/install-ros",
]


class ArgsDefinition(TypedDict):
    """Dictionary representing argument definitions for tasks."""

    # fmt: off
    help:        str
    default:     NotRequired[None | bool | str | list[str]]
    choices:     NotRequired[None | list[str]]
    nargs:       NotRequired[None | Union[int, str]]
    mutex:       NotRequired[None | str]
    # fmt: on


ArgsDefinitionCollection: TypeAlias = dict[str, ArgsDefinition]


class DefaultTaskDict(TypedDict):
    """Dictionary representing a default task configuration."""

    # fmt: off
    description:    str
    script:         str
    function:       None | str
    config_file:    NotRequired[None | str]
    depends_on:     NotRequired[list[str]]
    privileged:     NotRequired[bool]
    supercedes:     NotRequired[list[str]]
    args:           NotRequired[ArgsDefinitionCollection]
    # fmt: on


class CustomTaskDict(TypedDict):
    """Dictionary representing a custom task configuration."""

    # fmt: off
    config_file: NotRequired[str]
    args:        NotRequired[list[str]]
    # fmt: on


COMMON_TASK_DICT_FIELDS = set(get_type_hints(DefaultTaskDict).keys()) & set(
    get_type_hints(CustomTaskDict).keys()
)


class TaskDict(DefaultTaskDict, CustomTaskDict):
    """Dictionary representing a full task configuration."""

    pass


DefaultTaskDictCollection: TypeAlias = dict[str, DefaultTaskDict]
CustomTaskDictCollection: TypeAlias = dict[str, CustomTaskDict]
TaskDictCollection: TypeAlias = dict[str, TaskDict]


class ResolvedArgsDefinition(TypedDict):
    """Dictionary representing argument definitions for tasks."""

    # fmt: off
    help:        str
    default:     None | bool | str | list[str]
    choices:     None | list[str]
    nargs:       None | Union[int, str]
    mutex:       None | str
    # fmt: on


ResolvedArgsDefinitionCollection: TypeAlias = dict[str, ResolvedArgsDefinition]


class ResolvedDefaultTaskDict(TypedDict):
    """Dictionary representing a resolved default task configuration."""

    # fmt: off
    description:    str
    script:         Path
    function:       None | str
    config_file:    None | Path
    depends_on:     list[str]
    privileged:     bool
    supercedes:     list[str]
    args:           ResolvedArgsDefinitionCollection
    # fmt: on


class ResolvedCustomTaskDict(TypedDict):
    """Dictionary representing a resolved custom task configuration."""

    # fmt: off
    config_file: None | Path
    args:        list[str]
    # fmt: on


COMMON_RESOLVED_TASK_DICT_FIELDS = set(
    get_type_hints(ResolvedDefaultTaskDict).keys()
) & set(get_type_hints(ResolvedCustomTaskDict).keys())


class ResolvedTaskDict(ResolvedDefaultTaskDict, ResolvedCustomTaskDict):
    """Dictionary representing a full resolved task configuration."""

    pass


ResolvedDefaultTaskDictCollection: TypeAlias = dict[
    str, ResolvedDefaultTaskDict
]
ResolvedCustomTaskDictCollection: TypeAlias = dict[str, ResolvedCustomTaskDict]
ResolvedTaskDictCollection: TypeAlias = dict[str, ResolvedTaskDict]


@dataclass(frozen=True)
class ResolvedTask:
    """Represents a resolved task with its name, command, dependencies, and arguments."""

    # fmt: off
    name:        str             = field()
    command:     Command         = field()
    config_file: None | str      = field(default=None)
    depends_on:  tuple[str, ...] = field(default_factory=tuple)
    privileged:  bool            = field(default=False)
    args:        tuple[str, ...] = field(default_factory=tuple)
    # fmt: on
