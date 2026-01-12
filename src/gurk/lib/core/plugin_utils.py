# TODO: Move much of this to utils/common.py. Can any of this be moved to utils/plugins.py? If so, update docs accordingly.

import json
import os
import re
import shutil
from argparse import (
    SUPPRESS,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    ArgumentTypeError,
    Namespace,
    _ArgumentGroup,
)
from collections import defaultdict
from pathlib import Path
from typing import Iterator, NotRequired, Sequence, TypeAlias, TypedDict

import networkx as nx
from ruamel.yaml import YAML

from gurk.lib.logger import get_logger
from gurk.lib.utils.common import (
    PACKAGE_HOME_PATH,
    PACKAGE_SRC_PATH,
    YES_ANSWERS,
    FilePath,
    generate_random_path,
)
from gurk.lib.utils.remotes import (
    GitRef,
    clone_git_repo,
    is_git_repo,
    parse_git_ref,
)
from gurk.lib.utils.scripts import (
    ScriptBlockTypes,
    check_script_blocks,
    get_block_spans,
)
from gurk.lib.utils.system_info import SystemInfo
from gurk.lib.utils.tasks import (
    CustomTaskDictCollection,
    DefaultTaskDictCollection,
    ResolvedArgsDefinitionCollection,
    ResolvedCustomTaskDictCollection,
    ResolvedDefaultTaskDictCollection,
    TaskDictCollection,
)
from gurk.lib.utils.typed_dict import (
    fill_typed_dict,
    print_typed_dict_types,
    validate_typed_dict,
)
from gurk.lib.utils.yaml import load_yaml

#########################################################################################
#################################### Minor utilities ####################################
#########################################################################################


class PluginDefine(TypedDict):
    # fmt: off
    name:        str
    description: str
    tasks:       NotRequired[DefaultTaskDictCollection]
    # fmt: on


class PluginRun(TypedDict):
    options: NotRequired[dict[str, CustomTaskDictCollection]]
    default: CustomTaskDictCollection


class GurkPlugin(TypedDict):
    # fmt: off
    imports: NotRequired[list[GitRef | str]]
    define:  PluginDefine
    run:     PluginRun
    # fmt: on


class PluginRun(TypedDict):
    options: dict[str, ResolvedCustomTaskDictCollection]
    default: ResolvedCustomTaskDictCollection


class ResolvedPluginDefine(TypedDict):
    # fmt: off
    name:        str
    description: str
    tasks:       ResolvedDefaultTaskDictCollection


class ResolvedGurkPlugin(TypedDict):
    # fmt: off
    imports: list[GitRef | str]
    define:  ResolvedPluginDefine
    run:     PluginRun
    # fmt: on


class PluginRegistryEntry(TypedDict):
    local: str
    remote: GitRef | None
    # version: str # Keep? How to read remote repo versions?


PluginSpec: TypeAlias = str | FilePath | GitRef


def _get_plugin_dirs(
    home_registry: bool = True, package_registry: bool = True
) -> tuple[Path, ...]:
    """
    Get a tuple of plugin directories.

    :param home_registry: Whether to include the home plugin directory
    :type home_registry: bool
    :param package_registry: Whether to include the package plugin directory
    :type package_registry: bool
    :return: Tuple of plugin directories (home, package), depending on the input
    :rtype: tuple[Path, ...]
    """
    parent_paths: list[Path] = []
    if home_registry:
        parent_paths.append(PACKAGE_HOME_PATH)
    if package_registry:
        parent_paths.append(PACKAGE_SRC_PATH)

    possible_plugin_paths = [p / "plugins" for p in parent_paths]
    for p in possible_plugin_paths:
        p.mkdir(parents=True, exist_ok=True)

    return tuple(possible_plugin_paths)


def _get_plugin_registries(
    home_registry: bool = True, package_registry: bool = True
) -> tuple[Path, ...]:
    """
    Get a tuple of plugin registries.

    :param home_registry: Whether to include the home plugin registry
    :type home_registry: bool
    :param package_registry: Whether to include the package plugin registry
    :type package_registry: bool
    :return: Tuple of plugin registries (home, package), depending on the input
    :rtype: tuple[Path, ...]
    """
    possible_plugin_registries = [
        p / "registry.yaml"
        for p in _get_plugin_dirs(home_registry, package_registry)
    ]
    for p in possible_plugin_registries:
        p.touch(exist_ok=True)

    return tuple(possible_plugin_registries)


def get_combined_plugin_registry() -> dict[str, PluginRegistryEntry]:
    """
    Get the combined plugin registry from home and package registries.

    :return: Combined plugin registry
    :rtype: dict[str, PluginRegistryEntry]
    """
    home_registry_file, package_registry_file = _get_plugin_registries()
    home_registry = load_yaml(home_registry_file) or {}
    package_registry = load_yaml(package_registry_file) or {}

    # Combine registries, prioritizing home registry
    combined_registry = package_registry.copy()
    combined_registry.update(home_registry)

    return combined_registry


# TODO: See if new parse_git_ref causes secondary issues somewhere else
def _get_possible_plugin_entries(
    plugin: PluginSpec,
    home_registry: bool = True,
    package_registry: bool = True,
) -> tuple[PluginRegistryEntry | None, ...]:
    """
    Get possible plugin registry entries for a given plugin name.
        NOTE: This does not check the validity of the plugin yaml file.

    :param plugin: Name, FilePath, or GitRef of the plugin
    :type plugin: PluginSpec
    :param home_registry: Whether to check the home plugin registry
    :type home_registry: bool
    :param package_registry: Whether to check the package plugin registry
    :type package_registry: bool
    :return: Tuple of possible PluginRegistryEntry objects for the plugin, or None if not found
    :rtype: tuple[PluginRegistryEntry | None, ...]
    """
    plugin = str(plugin)

    # Get logger
    logger = get_logger()

    def _load_plugin(registry_file: Path) -> PluginRegistryEntry | None:
        registry: dict[str, PluginRegistryEntry] = (
            load_yaml(registry_file) or {}
        )

        # Get plugin entry
        remote_parsed = parse_git_ref(plugin)["url"]
        remote_entry = next(
            (
                v
                for v in registry.values()
                if v.get("remote")
                and remote_parsed == parse_git_ref(v["remote"])["url"]
            ),
            None,
        )
        if remote_entry:
            # Access plugin by remote
            entry = remote_entry
        elif plugin in registry:
            # Access plugin by name
            entry = registry[plugin]
        else:
            if plugin == "template-gurk-plugin":
                logger.debug(
                    f"Returning None, as entry is not found in {registry_file}"
                )
            return None

        # Validate structure
        if not validate_typed_dict(entry, PluginRegistryEntry):
            logger.debug(
                f"Invalid plugin registry entry {entry} for plugin '{plugin}' in registry '{registry_file}'."
            )
            return None

        # Resolve local path
        local_path = registry_file.parent / entry["local"]
        if not local_path.is_dir():
            logger.debug(
                f"Local path '{local_path}' for plugin '{plugin}' does not exist or is not a directory."
            )
            return None
        elif not (local_path / "gurk-plugin.yaml").is_file():
            logger.debug(
                f"Local path '{local_path}' for plugin '{plugin}' is missing 'gurk-plugin.yaml' file."
            )
            return None
        entry["local"] = str(local_path)

        return entry

    plugin_registries = _get_plugin_registries(home_registry, package_registry)
    if len(plugin_registries) == 1:
        return (_load_plugin(plugin_registries[0]),)
    else:
        return tuple(
            _load_plugin(registry_file) for registry_file in plugin_registries
        )


def get_plugin_entry(
    plugin: PluginSpec,
    home_registry: bool = True,
    package_registry: bool = True,
) -> PluginRegistryEntry | None:
    """
    Get the registry entry of a plugin (path, remote) if it exists locally.

    :param plugin: Name, FilePath, or GitRef of the plugin
    :type plugin: PluginSpec
    :param home_registry: Whether to check the home plugin registry
    :type home_registry: bool
    :param package_registry: Whether to check the package plugin registry
    :type package_registry: bool
    :return: Registry entry if the plugin exists locally, None otherwise
    :rtype: PluginRegistryEntry | None
    """
    possible_plugin_data = _get_possible_plugin_entries(
        plugin, home_registry, package_registry
    )
    plugin_data = tuple(p for p in possible_plugin_data if p is not None)

    # Logging
    logger = get_logger()
    if not plugin_data:
        logger.debug(
            f"ERROR: Plugin '{plugin}' does not exist locally in a valid form."
        )
    elif len(plugin_data) > 1:
        logger.debug(
            f"WARNING: Multiple entries found for plugin '{plugin}'. Using the first one."
        )

    return plugin_data[0] if plugin_data else None


def plugin_exists_locally(plugin: PluginSpec) -> bool:
    """
    Check if a plugin exists in the possible local plugin paths.

    :param plugin: Name, FilePath, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: True if the plugin exists locally, False otherwise
    :rtype: bool
    """
    return get_plugin_entry(plugin) is not None


def plugin_exists_remotely(plugin: GitRef) -> bool:
    """
    Check if a plugin exists in the possible remote plugin paths.

    :param plugin: GitRef of the plugin
    :type plugin: GitRef
    :return: True if the plugin exists remotely, False otherwise
    :rtype: bool
    """
    return is_git_repo(str(plugin))


def plugin_exists(plugin: PluginSpec) -> bool:
    """
    Check if a plugin exists either locally or remotely.

    :param plugin: Name, FilePath, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: True if the plugin exists, False otherwise
    :rtype: bool
    """
    return plugin_exists_locally(plugin) or plugin_exists_remotely(plugin)


def load_raw_plugin_yaml(plugin: PluginSpec) -> GurkPlugin | None:
    """
    Get the gurk-plugin.yaml configuration of a plugin if it exists locally.

    :param plugin: Name, FilePath, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: GurkPlugin configuration if the plugin exists locally, None otherwise
    :rtype: GurkPlugin | None
    """
    plugin_entry = get_plugin_entry(plugin)
    if not plugin_entry:
        return None

    if not check_local_plugin(plugin_entry["local"]):
        return None

    return load_yaml(Path(plugin_entry["local"]) / "gurk-plugin.yaml")


# TODO: Remove all non-debug log messages in commands, as this should suffice
def load_resolved_plugin_yaml(plugin: PluginSpec) -> ResolvedGurkPlugin | None:
    """
    Get the gurk-plugin.yaml configuration of a local plugin with
    - all paths resolved and converted to "Path" objects
    - missing properties filled with default values

    :param plugin: Name, FilePath, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: GurkPlugin configuration with resolved paths and filled properties if the plugin exists locally, None otherwise
    :rtype: ResolvedGurkPlugin | None
    """
    # Get logger
    logger = get_logger()

    plugin_yaml = load_raw_plugin_yaml(plugin)
    if not plugin_yaml:
        logger.warning(
            f"Plugin '{plugin}' is missing a valid 'gurk-plugin.yaml' file - not loading it."
        )
        return None
    else:
        logger.debug(f"Successfully loaded plugin '{plugin}'.")

    # Fill missing properties
    plugin_yaml: GurkPlugin = fill_typed_dict(plugin_yaml, GurkPlugin)

    # Expand task paths
    plugin_path = get_plugin_entry(plugin)["local"]
    for _, task in plugin_yaml["define"]["tasks"].items():
        # Expand script path
        task["script"] = str(Path(plugin_path) / task["script"])

        # Expand config_file path (if applicable)
        if task["config_file"] is not None:
            task["config_file"] = str(Path(plugin_path) / task["config_file"])

    return plugin_yaml


def get_plugin_data(
    plugin: PluginSpec,
) -> tuple[PluginRegistryEntry | None, ResolvedGurkPlugin | None]:
    """
    Get the registry entry and gurk-plugin.yaml configuration of a local plugin.

    :param plugin: Name, FilePath, or GitRef of the plugin
    :type plugin: PluginSpec
    :return: Tuple of PluginRegistryEntry and GurkPlugin configuration if the plugin exists locally, None each otherwise.
             If an entry exists but the yaml is invalid, returns (entry, None).
    :rtype: tuple[PluginRegistryEntry | None, ResolvedGurkPlugin | None]
    """
    plugin_entry = get_plugin_entry(plugin)
    if not plugin_entry:
        return None, None

    plugin_yaml = load_resolved_plugin_yaml(plugin)
    if not plugin_yaml:
        return plugin_entry, None

    return plugin_entry, plugin_yaml


def get_available_plugin_names() -> list[str]:
    """
    Get the names of all available local plugins.

    :return: List of available local plugin names
    :rtype: list[str]
    """
    combined_registry = get_combined_plugin_registry()
    return list(combined_registry.keys())


def get_combined_plugin_tasks() -> ResolvedDefaultTaskDictCollection:
    """
    Get the combined task definitions of all local plugins.

    :return: Dictionary of tasks from all local plugins
    :rtype: ResolvedDefaultTaskDictCollection
    """
    combined_tasks: TaskDictCollection = {}
    for plugin in get_available_plugin_names():
        plugin_yaml = load_resolved_plugin_yaml(plugin)
        if plugin_yaml:
            combined_tasks.update(plugin_yaml["define"]["tasks"])

    return combined_tasks


def iter_scripts() -> Iterator[Path]:
    """
    Yields all script files of installed plugins.

    :return: Iterator of Paths to script files
    :rtype: Iterator[Path]
    """
    all_tasks = get_combined_plugin_tasks()
    for task in all_tasks.values():
        yield task["script"]


def iter_configs() -> Iterator[Path]:
    """
    Yields all script files of installed plugins.

    :return: Iterator of Paths to script files
    :rtype: Iterator[Path]
    """
    all_tasks = get_combined_plugin_tasks()
    for task in all_tasks.values():
        if task.get("config_file"):
            yield task["config_file"]


def add_plugin_entry(
    plugin_name: str, plugins_entry: PluginRegistryEntry
) -> bool:
    """
    Add a plugin to the home plugin registry.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :param plugins_entry: Plugin registry entry
    :type plugins_entry: PluginRegistryEntry
    :return: True if the plugin was added successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check if the plugin already exists
    plugin_entry = get_plugin_entry(plugin_name)
    if plugin_entry:
        logger.debug(
            f"Plugin '{plugin_name}' already exists in some registry."
        )
        return False

    # Load home plugin registry
    registry_file = _get_plugin_registries(package_registry=False)[0]
    registry: dict[str, PluginRegistryEntry] = load_yaml(registry_file) or {}

    # Add plugin entry
    registry[plugin_name] = {
        "local": plugins_entry["local"],
        "remote": plugins_entry["remote"],
    }
    with open(registry_file, "w") as f:
        YAML().dump(registry, f)

    return True


def remove_plugin_entry(plugin_name: PluginSpec) -> None:
    """
    Remove a plugin from the home plugin registry.

    :param plugin_name: Name of the plugin
    :type plugin_name: PluginSpec
    """
    # Get logger
    logger = get_logger()

    # Check if the plugin exists
    plugin_entry = get_plugin_entry(plugin_name, package_registry=False)
    if not plugin_entry:
        logger.debug(
            f"Plugin '{plugin_name}' does not exist in home registry."
        )
        return

    # Load home plugin registry
    registry_file = _get_plugin_registries(package_registry=False)[0]
    registry: dict[str, PluginRegistryEntry] = load_yaml(registry_file) or {}

    # Remove plugin entry
    del registry[plugin_name]
    with open(registry_file, "w") as f:
        YAML().dump(registry, f)


# TODO: Use
def update_plugin_entry(
    plugin_name: str, local: str | None = None, remote: GitRef | None = None
) -> bool:
    """
    Update a plugin entry in any of the plugin registries.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :param local: New local path of the plugin
    :type local: str | None
    :param remote: New remote GitRef of the plugin
    :type remote: GitRef | None
    :return: True if the plugin was updated successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check args
    if local is None and remote is None:
        logger.debug("No fields to update for plugin entry.")
        return False

    # Load registry files and update entry
    registry_files = _get_plugin_registries()
    for registry_file in registry_files:
        registry: dict[str, PluginRegistryEntry] = (
            load_yaml(registry_file) or {}
        )

        # Check if plugin exists
        if plugin_name not in registry:
            continue

        # Update plugin entry
        if local is not None:
            registry[plugin_name]["local"] = local
        if remote is not None:
            registry[plugin_name]["remote"] = remote

        with open(registry_file, "w") as f:
            YAML().dump(registry, f)

        return True

    return False


class CleanHelpFormatter(ArgumentDefaultsHelpFormatter):
    """
    Custom formatter that:
      - hides default=None and default=False for boolean flags
      - annotates mutually exclusive args automatically
      - respects max_help_position
    """

    def __init__(self, prog):
        super().__init__(prog, max_help_position=60)

    def _get_help_string(self, action):
        if action.default not in (None, SUPPRESS):
            # A default is specified and is not purposefully suppressed
            # NOTE: Inludes boolean flags ("store_true"/"store_false")
            default_suffix = f"(default: {action.default!s})"
            if not action.help:
                return default_suffix
            else:
                return action.help + " " + default_suffix
        else:
            # No default specified or default is purposefully suppressed
            return action.help or ""


class GurkArgumentParser(ArgumentParser):
    """
    Custom ArgumentParser that uses CleanHelpFormatter and adds common gurk CLI options.
    """

    def __init__(
        self,
        add_verbose_arg: bool = True,
        add_non_interactive_arg: bool = True,
        add_force_arg: bool = False,
        add_task_args: bool = False,
        allow_complex_types: bool = True,
        *args,
        **kwargs,
    ):
        # Some gurk internal variables
        self.required_group_title = "required arguments"
        self.add_non_interactive_arg = add_non_interactive_arg
        self.allow_complex_types = allow_complex_types

        # Use CleanHelpFormatter
        kwargs["formatter_class"] = lambda prog: CleanHelpFormatter(prog)

        # Call super init
        super().__init__(*args, **kwargs)

        # Add logger options
        if add_verbose_arg:
            self.add_argument(
                "-v",
                "--verbose",
                action="store_true",
                help="Enable verbose output",
            )
        if add_non_interactive_arg:
            self.add_argument(
                "--non-interactive",
                action="store_true",
                help="Run in non-interactive mode (disable prompts)",
            )
        if add_task_args:
            self._add_task_args()
        if add_force_arg:
            self.add_argument(
                "-f",
                "--force",
                action="store_true",
                help="Force execution of task(s) even if they don't need to run",
            )

    def _add_task_args(self) -> None:
        """
        Add common task arguments to the parser.

        :raises ArgumentTypeError: If argument validation fails
        """

        # Add system-info argument
        def json_dict(value: str) -> SystemInfo:
            """
            Validate that the input is a JSON object (dictionary).

            :param value: Input string
            :type value: str
            :return: Parsed JSON object
            :rtype: dict
            :raises ArgumentTypeError: If the input is not a valid JSON object
            """
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as e:
                raise ArgumentTypeError(f"Invalid JSON for --system-info: {e}")
            if not isinstance(parsed, dict):
                raise ArgumentTypeError(
                    "--system-info must be a JSON object (dictionary)"
                )
            return parsed

        self.add_argument(
            "--system-info",
            type=json_dict if self.allow_complex_types else str,
            required=True,
            help="JSON object with system information",
        )

        # Add config-file argument
        def existing_path(value: str) -> Path:
            """
            Validate that the input path exists.

            :param value: Input path string
            :type value: str
            :return: Path object
            :rtype: Path
            :raises ArgumentTypeError: If the path does not exist
            """
            path = Path(value)
            if not path.exists():
                raise ArgumentTypeError(f"Config file not found: {path}")
            return path

        self.add_argument(
            "--config-file",
            type=existing_path if self.allow_complex_types else str,
            default=None,
            help="Path to an existing config file",
        )

    def add_required_group(self) -> _ArgumentGroup:
        """
        Add a 'required arguments' group to the parser.

        :return: The created argument group
        :rtype: _ArgumentGroup
        """
        return self.add_argument_group(self.required_group_title)

    # TODO: Clean this up
    def extend_arguments(
        self, args_dict: ResolvedArgsDefinitionCollection
    ) -> None:
        """
        Extend the parser with arguments defined in a plugin.

        :param args_dict: Dictionary of argument definitions
        :type args_dict: ResolvedArgsDefinitionCollection
        """

        def make_wildcard_validator(patterns: list[str]):
            """
            Create:
            - an argparse type() validator supporting '*' wildcards
            - a matching metavar string
            """

            regexes = [
                re.compile("^" + re.escape(p).replace(r"\*", ".*") + "$")
                for p in patterns
            ]

            quoted = ", ".join(f"'{p}'" for p in patterns)
            metavar = "{" + ",".join(patterns) + "}"

            def validate(value: str) -> str:
                if any(rx.match(value) for rx in regexes):
                    return value
                raise ArgumentTypeError(
                    f"invalid choice: {value!r} (choose from {quoted})"
                )

            return validate, metavar

        # Collect mutually exclusive groups
        mutex_groups = defaultdict(list)
        for name, spec in args_dict.items():
            mutex = spec.get("mutex")
            if mutex:
                mutex_groups[mutex].append(name)

        argparse_mutex_groups = {
            name: self.add_mutually_exclusive_group() for name in mutex_groups
        }

        for name, spec in args_dict.items():
            help_text = spec.get("help")
            default = spec.get("default")
            nargs = spec.get("nargs")
            choices = spec.get("choices")

            kwargs = {}

            if help_text is not None:
                kwargs["help"] = help_text

            if choices is not None:
                validator, metavar = make_wildcard_validator(choices)
                kwargs["type"] = validator
                kwargs["metavar"] = metavar

            # --- Boolean flags ---
            if isinstance(default, bool):
                if nargs is not None:
                    raise ValueError(
                        f"Boolean flag '{name}' must not define nargs"
                    )

                kwargs["action"] = (
                    "store_true" if default is False else "store_false"
                )
                kwargs["default"] = default

            # --- Non-boolean arguments ---
            else:
                # if has_default:
                if default is not None:
                    # optional argument
                    kwargs["default"] = default
                elif nargs not in ("?", "*"):
                    # required argument
                    kwargs["required"] = True

                if nargs is not None:
                    kwargs["nargs"] = nargs

            # Choose correct target (parser or mutex group)
            mutex = spec.get("mutex")
            target = argparse_mutex_groups[mutex] if mutex else self

            target.add_argument(name, **kwargs)

    def extend_task_arguments(self, task_name: str) -> None:
        """
        Extend the parser with task-specific arguments defined in a plugin, if any.

        :param plugin: Plugin specification
        :type plugin: PluginSpec
        :raises ValueError: If the plugin YAML could not be loaded
        """
        plugin = task_name.split("/", 1)[0]
        plugin_yaml: ResolvedGurkPlugin = load_resolved_plugin_yaml(plugin)
        if not plugin_yaml:
            raise ValueError(f"Plugin '{plugin}' could not be loaded")

        try:
            task_args = plugin_yaml["define"]["tasks"][task_name]["args"]
            self.extend_arguments(task_args)
        except KeyError as e:
            self.error(
                f"Key 'define'/'tasks'/'{task_name}'/'args' not "
                f"found in plugin '{plugin}' YAML. Broken link: {e}"
            )

    def _reorder_actions(self):
        """
        Reorder actions to have required ones first.
        """
        # Reorder action groups to have 'required arguments' first
        required_group = None
        for g in self._action_groups:
            if g.title == self.required_group_title:
                required_group = g
                break
        if required_group:
            self._action_groups.remove(required_group)
            self._action_groups.insert(0, required_group)

    def print_help(self, file=None) -> None:
        # Reorder action groups to have 'required arguments' first
        self._reorder_actions()

        # Call the original print_help
        return super().print_help(file)

    def parse_args(
        self, args: Sequence[str] | None = None, namespace: None = None
    ) -> Namespace:
        # Reorder action groups to have 'required arguments' first
        self._reorder_actions()

        # Call the original parse_args
        args = super().parse_args(args, namespace)

        # Get non-interactive mode from env var if not specified
        if self.add_non_interactive_arg and not args.non_interactive:
            args.non_interactive = (
                os.getenv("GURK_NON_INTERACTIVE", "false").lower()
                in YES_ANSWERS
            )

        return args


#########################################################################################
################################### Command utilities ###################################
#########################################################################################


def check_local_plugin(plugin_path: FilePath) -> bool:
    """
    Check if a local plugin is valid.
        NOTE: All imported plugins (recursively) must also be local and valid.

    :param plugin_path: Path to the local plugin
    :type plugin_path: FilePath
    :return: True if the plugin is valid, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Directed graphs for checking cycles
    imports_graph = nx.DiGraph()
    task_dependency_graph = nx.DiGraph()
    task_supercedes_graph = nx.DiGraph()

    # Save available tasks
    available_tasks: DefaultTaskDictCollection = dict()

    def _check_local_plugin(_plugin_path: Path) -> bool:
        def error(message: str) -> bool:
            logger.error(f"'{_plugin_path}': {message}")

        # Load gurk-plugin.yaml
        plugin: GurkPlugin = load_yaml(_plugin_path / "gurk-plugin.yaml")
        if not plugin:
            error(
                f"Plugin source '{_plugin_path}' has no 'gurk-plugin.yaml' file or it is invalid YAML."
            )
            return False

        # Validate structure
        plugin_without_helpers: GurkPlugin = {
            k: v
            for k, v in plugin.items()
            if isinstance(k, str) and not k.startswith("_")
        }
        if not validate_typed_dict(plugin_without_helpers, GurkPlugin):
            error(
                f"Plugin at '{_plugin_path}' has invalid structure. Expected:"
            )
            print_typed_dict_types(GurkPlugin)
            return False

        ## Check that the plugin name is unique
        plugin_definition: PluginDefine = plugin["define"]
        plugin_name = plugin_definition["name"]
        existing_plugin = get_plugin_entry(plugin_name)
        if (
            existing_plugin
            and Path(existing_plugin["local"]) != _plugin_path.resolve()
        ):
            error(
                f"Plugin name '{plugin_name}' is already used by another plugin at '{existing_plugin['local']}'."
            )
            return False

        ## Check plugin description
        min_description_length = 10
        if len(plugin_definition["description"]) < min_description_length:
            error(
                f"Plugin '{plugin_name}' description is too short. Please provide a more "
                f"detailed description (at least {min_description_length} characters)."
            )
            return False

        ## Check each task field
        for task_name, task in plugin_definition["tasks"].items():
            # Check task name
            plugin_prefix, remaining = (task_name.split("/", 1) + [None])[:2]
            if plugin_prefix != plugin_name or not remaining:
                error(
                    f"Task '{task_name}' has an invalid name. Its name should be '{plugin_name}/<task_name>'"
                )
                return False

            # Check task description
            if len(task["description"]) < min_description_length:
                error(
                    f"Task '{task_name}' description is too short. Please provide a more "
                    f"detailed description (at least {min_description_length} characters)."
                )
                return False

            # Check 'script' field
            ## Existence
            script = _plugin_path / task["script"]
            if not script.is_file():
                error(
                    f"Task '{task_name}' script file '{script}' does not exist."
                )
                return False
            ## Validity
            errors = check_script_blocks(script)
            if errors:
                error(
                    f"Task '{task_name}' script '{script}' has errors:\n"
                    + "\n".join(errors)
                )
                return False

            # Check 'function' field
            blocks = get_block_spans(script)
            if task["function"] is None:
                desired_block_type = ScriptBlockTypes.ENTRYPOINT
            else:
                desired_block_type = ScriptBlockTypes.FUNCTION
            if not any(
                b["name"] == task["function"]
                for b in blocks
                if b["type"] == desired_block_type
            ):
                error(
                    f"Task '{task_name}' {'function ' + task['function'] if task['function'] else 'entrypoint'} does not exist in script '{script}'."
                )
                return False

            # Check 'config_file' field
            if task.get("config_file") is not None:
                config_file = _plugin_path / task["config_file"]
                if not config_file.is_file():
                    error(
                        f"Task '{task_name}' config file '{config_file}' does not exist."
                    )
                    return False

            # Check 'args' field
            arg_start = f"--{plugin_name}-"
            arg_names = [arg_name for arg_name in task.get("args", {}).keys()]
            invalid_args = [
                arg_name
                for arg_name in arg_names
                if not arg_name.startswith(arg_start)
            ]
            if invalid_args:
                error(
                    f"Task '{task_name}' has an invalid arg names {invalid_args}. "
                    f"Arg names must be '{arg_start}<remaining>'."
                )
                return False
            if len(arg_names) != len(set(arg_names)):
                error(
                    f"Task '{task_name}' has duplicate arg names in its 'args' section."
                )
                return False

        # Check that the 'imports' section is valid
        imports = plugin.get("imports", [])
        if not isinstance(imports, list) or not all(
            isinstance(imp, str) for imp in imports
        ):
            error(
                f"Plugin 'imports' section is not a list of strings, but of type '{type(imports)}'."
            )
            return False

        def check_graph(graph: nx.DiGraph, field: str) -> bool:
            """
            Check for cycles and missing refs in a directed graph.

            :param graph: The directed graph to check
            :type graph: nx.DiGraph
            :param field: The field being checked (for logging purposes)
            :type field: str
            :return: True if no cycles are found, False otherwise
            :rtype: bool
            """
            try:
                cycle = nx.find_cycle(graph)
                if cycle:
                    error(
                        f"Circular dependency detected in '{field}' field: {cycle}"
                    )
                    return False
            except nx.NetworkXNoCycle:
                # No cycle detected
                pass
            return True

        ## Check that imported plugins exist and are valid
        imports_graph.add_node(plugin_name)
        for imp in imports:
            # Check that imported plugins exist in the desired location
            if not plugin_exists_locally(imp):
                msg = f"Imported plugin '{imp}' does not exist locally."
                if plugin_exists_remotely(imp):
                    msg += f" You can pull it via 'gurk pull {imp}'."
                error(msg)
                return False

            # Check the imports graph for cycles
            imports_graph.add_edge(plugin_name, imp)
            if not check_graph(imports_graph, "imports"):
                return False

            # Check imported plugin
            if not _check_local_plugin(Path(get_plugin_entry(imp)["local"])):
                error(f"Imported plugin '{imp}' is invalid.")
                return False

        # Add defined tasks to available tasks
        task_names = list(plugin_definition["tasks"].keys())
        available_tasks.update(plugin_definition["tasks"])

        def expand_graph(graph: nx.DiGraph, field: str) -> bool:
            """
            Expand a directed graph with edges from a task field.
                NOTE: The direction is the same, as this is only used for cycle detection.

            :param graph: The directed graph to expand
            :type graph: nx.DiGraph
            :param field: The field from which to add edges
            :type field: str
            :return: True if successful, False if an unknown task is found
            :rtype: bool
            """
            graph.add_nodes_from(task_names)
            for task_name, task in plugin_definition["tasks"].items():
                for dep in task.get(field, []):
                    if dep not in available_tasks:
                        error(
                            f"Task '{task_name}' uses unknown task '{dep}' in '{field}' field."
                        )
                        return False
                    graph.add_edge(task_name, dep)

            return True

        # Check the task dependency graph
        dependency_field = "depends_on"
        if not expand_graph(task_dependency_graph, dependency_field):
            return False
        elif not check_graph(task_dependency_graph, dependency_field):
            return False

        # Check the task supercedes graph
        supercedes_field = "supercedes"
        if not expand_graph(task_supercedes_graph, supercedes_field):
            return False
        elif not check_graph(task_supercedes_graph, supercedes_field):
            return False

        # Check 'run' section
        plugin_run: PluginRun = plugin["run"]
        for option_name, option in [
            ("default", plugin_run["default"]),
            *plugin_run.get("options", {}).items(),
        ]:
            # Check that all tasks in the option are defined
            for task_name in option.keys():
                if task_name not in available_tasks:
                    error(
                        f"Task '{task_name}' in 'run' section is not defined in this or any imported plugins."
                    )
                    return False

            # Check that all args in the option are defined
            for task_name, option_spec in option.items():
                # Create a temporary parser to validate args
                parser = GurkArgumentParser(
                    add_verbose_arg=False,
                    add_non_interactive_arg=False,
                    add_force_arg=True,
                )
                allowed_args = available_tasks[task_name].get("args", {})
                parser.extend_arguments(allowed_args)

                # Override parser.error to raise exception instead of exiting
                def raise_error(message):
                    raise ValueError(message)

                parser.error = raise_error

                # Validate args
                try:
                    parser.parse_args(option_spec.get("args", []))
                except ValueError as e:
                    error(e)
                    return False

            # Check that at least one task is being run.
            # If any tasks are defined in the plugin, that at least one of them must be enabled
            enabled_tasks = {k: v for k, v in option.items() if v["enabled"]}
            if not enabled_tasks:
                error(
                    "Plugin 'run' section has an option with no enabled tasks."
                )
                return False
            if plugin_definition.get("tasks") and not set(
                plugin_definition["tasks"].keys()
            ) & set(enabled_tasks.keys()):
                error(
                    "Plugin 'run' section has an option with no enabled tasks from this plugin."
                )
                return False

            # Check that no two tasks that supercede each other are enabled together
            for u, v in task_supercedes_graph.edges():
                if u in enabled_tasks and v in enabled_tasks:
                    error(
                        f"Tasks '{u}' and '{v}' that supercede each other are "
                        f"both enabled in the same 'run' option '{option_name}'."
                    )
                    return False

        # All checks passed
        return True

    # Check plugin
    return _check_local_plugin(Path(plugin_path))


def pull_plugin(plugin: GitRef) -> bool:
    """
    Import a plugin from a remote Git repository.

    :param plugin: GitRef of the plugin to import
    :type plugin: GitRef
    :return: True if the plugin was imported successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    def error(message: str, _temp_plugin_path: Path | None = None):
        """
        Log an error message and clean up temporary plugin path if provided.

        :param message: Error message to log
        :type message: str
        :param _temp_plugin_path: Temporary plugin path to clean up
        :type _temp_plugin_path: Path | None
        """
        logger.error(message + ". Skipping...")
        if _temp_plugin_path is not None:
            shutil.rmtree(_temp_plugin_path)

    # Check if plugin with same remote already exists
    if get_plugin_entry(plugin):
        error(
            f"Plugin with remote '{plugin}' already exists locally. Please remove it "
            f"via 'gurk remove {plugin}' first or update it via 'gurk update {plugin}'"
        )
        return False

    # See if plugin source is valid
    if not plugin_exists_remotely(plugin):
        error(
            f"Remote plugin source '{plugin}' does not exist or is not a valid git repository"
        )
        return False

    # Import plugin to temporary directory
    temp_plugin_path = generate_random_path(
        prefix="gurk_plugin_import_", create=False
    )
    temp_plugin_path = clone_git_repo(plugin, temp_plugin_path)
    if not temp_plugin_path:
        error(f"Failed to clone remote plugin repository '{plugin}'")
        return False

    # Load gurk-plugin.yaml
    gurk_plugin: GurkPlugin = load_resolved_plugin_yaml(plugin)
    if not gurk_plugin:
        error(
            f"Failed to load a (valid) 'gurk-plugin.yaml' from plugin at '{plugin}'",
            temp_plugin_path,
        )
        return False

    # Add plugin
    plugin_name = gurk_plugin["define"]["name"]
    plugin_path = PACKAGE_HOME_PATH / "plugins" / plugin_name
    ## Add plugin folder
    shutil.move(temp_plugin_path, plugin_path)
    ## Add plugin registry entry
    add_plugin_entry(
        plugin_name,
        PluginRegistryEntry(
            local=str(plugin_path),
            remote=plugin,
        ),
    )


def remove_plugin(plugin: PluginSpec) -> None:
    """
    Remove a locally installed plugin.

    :param plugin: Name, FilePath, or GitRef of the plugin to remove
    :type plugin: PluginSpec
    """
    # Get logger
    logger = get_logger()

    # Get plugin entry
    plugin_entry = get_plugin_entry(plugin)
    if not plugin_entry:
        logger.error(f"Plugin '{plugin}' is not installed.")
        return

    # Get plugin name
    plugin_data = load_resolved_plugin_yaml(plugin)
    plugin_name = plugin_data["define"]["name"]

    # Remove plugin folder
    plugin_path = Path(plugin_entry["local"])
    if plugin_path.is_dir():
        shutil.rmtree(plugin_path)

    # Remove plugin registry entry
    remove_plugin_entry(plugin_name)
