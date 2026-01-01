import textwrap
from copy import deepcopy
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import networkx as nx

from cmstp.cli.utils import CORE_COMMANDS
from cmstp.core.logger import Logger
from cmstp.utils.cli import CoreCliArgs
from cmstp.utils.common import DEFAULT_CONFIG_FILE, get_script_path
from cmstp.utils.scripts import Command
from cmstp.utils.tasks import (
    DEFAULT_CUSTOM_CONFIG,
    TASK_PROPERTIES_CUSTOM,
    TASK_PROPERTIES_DEFAULT,
    ResolvedTask,
    TaskDictCollection,
    get_invalid_tasks_from_task_dict_collection,
    print_expected_task_fields,
)
from cmstp.utils.yaml import load_yaml, overlay_dicts


@dataclass
class TaskProcessor:
    """Processes tasks to run by resolving task properties."""

    # fmt: off
    logger:              Logger             = field(repr=False)
    processed_args:      CoreCliArgs        = field(repr=False)

    enable_all:          bool               = field(init=False, default=False)
    enable_dependencies: bool               = field(init=False, default=False)
    resolved_tasks:      List[ResolvedTask] = field(init=False, repr=False, default=None)

    # Internal
    _default_cfg_path: Path                 = field(init=False, repr=False, default=DEFAULT_CONFIG_FILE)
    _default_config:   TaskDictCollection   = field(init=False, repr=False, default=None)
    _allowed_args:     Dict[str, List[str]] = field(init=False, repr=False, default_factory=dict)
    _dependency_graph: nx.DiGraph           = field(init=False, repr=False, default=None)
    _supercedes_graph: nx.DiGraph           = field(init=False, repr=False, default=None)
    # fmt: on

    def __post_init__(self):
        # (Internal) Check default config file
        self._default_config = self.check_default_config()

        # Add CLI options
        self.enable_all = self.processed_args.enable_all
        self.enable_dependencies = self.processed_args.enable_dependencies

        # Check custom config file
        if self.processed_args.config_file is not None:
            custom_config = load_yaml(self.processed_args.config_file)
            custom_config = self.check_config(custom_config)
        else:
            self.logger.debug(
                "No valid config file is specified, thus only cli tasks (if any) will be enabled"
            )
            custom_config = {}

        # Check custom tasks
        custom_tasks = self.check_config(self.process_custom_tasks())

        # Merge default and custom config
        tasks: TaskDictCollection = overlay_dicts(
            [self._default_config, custom_config, custom_tasks],
            allow_default=True,
        )

        # Enable all tasks (that are not explicitly disabled) if enable_all is set
        if self.enable_all:
            self.logger.debug(
                "Enabling all tasks that are not explicitly disabled"
            )
            for task in tasks.values():
                if "enabled" not in task:
                    task["enabled"] = True

        # Disable all tasks that don't belong to the current cmstp command
        for task_name, task in tasks.items():
            if not task_name.startswith(self.processed_args.cmstp_cmd):
                self.logger.debug(
                    f"Disabling task '{task_name}', as it does not "
                    f"belong to the '{self.processed_args.cmstp_cmd}' command"
                )
                task["enabled"] = False

        # Fill all missing custom fields in other tasks
        tasks = {
            task_name: overlay_dicts([DEFAULT_CUSTOM_CONFIG, task])
            for task_name, task in tasks.items()
        }

        # Resolve and check config file paths for all tasks
        tasks = self.resolve_config_directory(tasks)

        # Disable all tasks not belonging to the current cmstp command
        # NOTE: '--enable-dependencies' may thus be required even if '--enable-all'
        #       is passed, to enable dependencies belonging to other cmstp commands
        for task_name, task in tasks.items():
            if not task_name.startswith(self.processed_args.cmstp_cmd):
                self.logger.debug(
                    f"Disabling task '{task_name}', as it does not "
                    f"belong to the '{self.processed_args.cmstp_cmd}' command"
                )
                task["enabled"] = False

        # Check dependency and supercedes graphs
        tasks = self.resolve_graphs(tasks)

        # Count enabled tasks
        enabled_task_names = [
            name for name, task in tasks.items() if task["enabled"]
        ]
        n_enabled = len(enabled_task_names)
        if n_enabled == 0:
            self.logger.fatal(
                "There are no enabled tasks (anymore). Nothing to do"
            )
        else:
            self.logger.debug(
                f"Final enabled tasks ({n_enabled}): {enabled_task_names}"
            )

        # Create logging directory
        self.logger.create_log_dir()

        # Convert to ResolvedTask list
        self.resolved_tasks = []
        for task_name, task in tasks.items():
            if not task["enabled"]:
                continue

            resolved_task = ResolvedTask(
                name=task_name,
                command=Command(task["script"], task["function"]),
                config_file=task["config_file"],
                depends_on=tuple(task["depends_on"]),
                privileged=task["privileged"],
                args=tuple(task["args"]),
            )
            self.resolved_tasks.append(resolved_task)

    @staticmethod
    def check_allowed(
        allowed_args: List[str],
        args: Union[str, List[str]],
        allow_default: bool = False,
    ) -> Tuple[List[str], bool]:
        """
        Check if an argument is in the allowed list.
        If allowed_args is None, any argument is allowed.

        :param allowed_args: List of allowed arguments
        :type allowed_args: List[str]
        :param args: Argument or list of arguments to check
        :type args: Union[str, List[str]]
        :param allow_default: Whether to allow 'default' as a valid argument
        :type allow_default: bool
        :return: Tuple of (list of wrong arguments, is valid)
        :rtype: Tuple[List[str], bool]
        """

        def _check_single_allowed(arg: str) -> bool:
            """
            Check if a single argument is allowed, supporting wildcard '*'

            :param allowed_args: List of allowed arguments
            :type allowed_args: List[str]
            :param arg: Argument to check
            :type arg: str
            :return: Whether the argument is allowed
            :rtype: bool
            """
            allowed = [
                *allowed_args,
                "--force",
                *(["default"] if allow_default else []),
            ]
            return any(
                fnmatchcase(arg, allowed_arg) for allowed_arg in allowed
            )

        if isinstance(args, str):
            is_allowed = _check_single_allowed(args)
            wrong_args = [] if is_allowed else [args]
            return wrong_args, is_allowed
        else:  # List[str]
            wrong_args = [
                arg for arg in args if not _check_single_allowed(arg)
            ]
            return wrong_args, not wrong_args

    def check_default_config(self) -> TaskDictCollection:
        """
        Check that the default config file is valid.

        :return: Default config tasks
        :rtype: TaskDictCollection
        """

        def fatal(msg: str, task_name: Optional[str] = None) -> None:
            """
            Helper to log fatal errors

            :param msg: Error message
            :type msg: str
            :param task_name: Name of the task where the error occurred
            :type task_name: Optional[str]
            """
            self.logger.fatal(
                f"Error in default config file {self._default_cfg_path}: {f'{task_name}:' if task_name else ''} {msg}"
            )

        # Check file exists and is not empty
        default_config = load_yaml(self._default_cfg_path)
        if default_config is None:
            fatal("File does not exist or is not valid YAML")
        if not default_config:
            fatal("File is empty")
        if not isinstance(default_config, dict):
            fatal(
                "File does not define a dict, but a "
                + type(default_config).__name__
            )

        # Remove helpers
        defaults = default_config["_defaults"]
        default_config = {
            k: overlay_dicts([defaults, v])
            for k, v in default_config.items()
            if isinstance(k, str) and not k.startswith("_")
        }

        # Check structure (incl. types)
        invalid_tasks = get_invalid_tasks_from_task_dict_collection(
            default_config, True
        )
        if invalid_tasks:
            fatal_msg = textwrap.dedent(
                f"""\
                Some tasks have extra or missing fields, or use incorrect types: {invalid_tasks}
                [cyan]Required structure for tasks in the default config[/cyan]:
            """
            )
            fatal(fatal_msg + print_expected_task_fields(default=True))

        # Check everything else
        existing_scripts = set()
        for task_name, task in default_config.items():
            # Check task name
            task_command = task_name.split("-")[0]
            if task_command not in CORE_COMMANDS:
                fatal(
                    f"Task command ('{task_command}') does not exist",
                    task_name,
                )

            # Check 'description' field
            if not task["description"]:
                fatal("Description is empty", task_name)

            # Resolve 'script' field
            if not task["script"]:
                fatal(
                    "Script is either null, empty or invalid",
                    task_name,
                )
            else:
                try:
                    task["script"] = get_script_path(
                        task["script"], task_name.split("-")[0]
                    )
                except ValueError as e:
                    fatal(str(e), task_name)

            # Check existence of script & function fields
            try:
                script_command = Command(task["script"], task["function"])
            except Exception as e:
                fatal(str(e), task_name)

            # Check for duplicate (script, function) pairs
            if script_command in existing_scripts:
                fatal(
                    f"Duplicate (script, function) pair: {script_command}",
                    task_name,
                )
            else:
                existing_scripts.add(script_command)

            # Check 'depends_on' field (must refer to existing tasks)
            for dep in task["depends_on"]:
                if dep not in default_config:
                    fatal(f"'{dep}' dependency task does not exist", task_name)

            # Check default args are allowed
            wrong_args, is_allowed = self.check_allowed(
                task["args"]["allowed"], task["args"]["default"]
            )
            if not is_allowed:
                fatal(
                    f"Some default args ({wrong_args}) are not in allowed args {task['args']['allowed']}",
                    task_name,
                )
            self._allowed_args[task_name] = task["args"]["allowed"]
            task["args"] = task["args"]["default"]

        # Build and check dependency and supercedes graphs
        def _build_and_check_task_graph(attribute: str) -> nx.DiGraph:
            # Create directed graph
            graph = nx.DiGraph()
            for task_name, task in default_config.items():
                graph.add_node(task_name)

            # Check references and add edges
            missing_refs = []
            for task_name, task in default_config.items():
                for ref in task[attribute]:
                    # Missing reference
                    if ref not in default_config:
                        missing_refs.append(
                            f"'{attribute}' reference '{ref}' "
                            f"for '{task_name}' not found"
                        )
                    # Add edge
                    else:
                        if attribute == "depends_on":
                            graph.add_edge(ref, task_name)
                        elif attribute == "supercedes":
                            graph.add_edge(task_name, ref)

            # Check for missing references
            if missing_refs:
                self.logger.fatal(
                    f"Default config: Some task '{attribute}' fields "
                    f"contain missing references: {missing_refs}"
                )

            # Check for cycles
            if not nx.is_directed_acyclic_graph(graph):
                self.logger.fatal(
                    f"Default config: {attribute.capitalize()} graph has cycles between: "
                    f"{list(nx.simple_cycles(graph))[0]}"
                )

            return graph

        self._dependency_graph = _build_and_check_task_graph("depends_on")
        self._supercedes_graph = _build_and_check_task_graph("supercedes")

        self.logger.debug("Default config file is valid")
        return default_config

    def check_config(self, config: Dict[str, Any] = {}) -> TaskDictCollection:
        """
        Check that the given config is valid.

        :return: Custom config tasks
        :rtype: TaskDictCollection
        """

        def warning(msg: str) -> None:
            """
            Helper to log warning messages

            :param msg: Warning message
            :type msg: str
            """
            self.logger.warning(f"Warning in config: {msg}")

        def check_option(option: str) -> None:
            """
            Helper to check and set a boolean option from the custom config.

            :param option: Option name (same as attribute name)
            :type option: str
            """
            if option in config:
                value = config.pop(option)
                if not isinstance(value, bool):
                    warning(
                        f"Ignoring '{option}' value - must be "
                        f"a boolean, not a {type(value).__name__}"
                    )
                else:
                    current_value = getattr(self, option)
                    setattr(self, option, current_value | value)

        # Check for "enable_all" parameter
        check_option("enable_all")

        # Check for "enable_dependencies" parameter
        check_option("enable_dependencies")

        # Add defaults for missing optional fields. Used to check structure of custom config tasks
        default_dict = deepcopy(DEFAULT_CUSTOM_CONFIG)
        for common_key in (
            TASK_PROPERTIES_DEFAULT.keys() & TASK_PROPERTIES_CUSTOM.keys()
        ):
            # Keep default value if not provided in config
            default_dict[common_key] = "default"
        filled_tasks = deepcopy(config)
        for task_name, task in config.items():
            # Quick check
            if not isinstance(task, dict):
                self.logger.warning(
                    f"Disabling task '{task_name}' because it is not "
                    f"defined by a dict, but a {type(task).__name__}"
                )
                filled_tasks[task_name] = default_dict
            else:
                filled_tasks[task_name] = overlay_dicts([default_dict, task])

        # Check structure (incl. types)
        invalid_tasks = get_invalid_tasks_from_task_dict_collection(
            filled_tasks, False
        )
        if invalid_tasks:
            warning_msg = textwrap.dedent(
                f"""\
                Some tasks that have extra fields or are trying to override default fields are disabled: {invalid_tasks}
                [cyan]Required structure for tasks in the custom config[/cyan] (all fields optional):
            """
            )
            warning(warning_msg + print_expected_task_fields(default=False))
            for task_name in invalid_tasks:
                filled_tasks[task_name] = default_dict

        # Remove tasks that are not in default config
        final_tasks = deepcopy(filled_tasks)
        for task_name, task in filled_tasks.items():
            if task_name not in self._default_config:
                self.logger.warning(
                    f"Task '{task_name}' in is removed because "
                    f"it is not defined in the default config"
                )
                final_tasks.pop(task_name)

        # Check args
        for task_name, task in final_tasks.items():
            # Check custom args are allowed
            wrong_args, is_allowed = self.check_allowed(
                self._allowed_args[task_name], task["args"], True
            )
            if not is_allowed:
                warning(
                    f"Task '{task_name}' was disabled because some custom "
                    f"args ({wrong_args}) are not in allowed args "
                    f"{self._allowed_args[task_name]}"
                )
                task["enabled"] = False

        self.logger.debug("Config is valid")
        return final_tasks

    def process_custom_tasks(self) -> TaskDictCollection:
        """
        Process custom tasks specified in the command line (e.g. `task_name:arg1:arg2:...`).

        :return: Processed custom config tasks
        :rtype: TaskDictCollection
        """
        processed_tasks = dict()
        for task_str in self.processed_args.tasks:
            parts = [p for p in task_str.split(":") if p]
            task_name = parts[0]
            task_args = parts[1:]

            processed_tasks[task_name] = {"enabled": True}
            if task_args:
                processed_tasks[task_name]["args"] = task_args

        if not processed_tasks:
            self.logger.debug("No custom tasks were specified")

        return processed_tasks

    def resolve_config_directory(
        self, tasks: TaskDictCollection
    ) -> TaskDictCollection:
        """
        Resolve and check config file paths for all tasks.

        :param tasks: Tasks to process
        :type tasks: TaskDictCollection
        :return: Processed tasks
        :rtype: TaskDictCollection
        """
        for task_name, task in tasks.items():
            if task["config_file"] is not None:
                config_file = (
                    self.processed_args.config_directory
                    / task_name.split("-")[0]
                    / task["config_file"]
                ).resolve()

                if not config_file.is_file():
                    task["config_file"] = None
                    task["enabled"] = False
                    self.logger.warning(
                        f"Task '{task_name}' was disabled because its "
                        f"config file does not exist: '{config_file}'"
                    )
                else:
                    task["config_file"] = str(config_file)

        self.logger.debug("Resolved config file paths for all tasks")
        return tasks

    def resolve_graphs(self, tasks: TaskDictCollection) -> TaskDictCollection:
        """
        Resolve enable/disable rules based on dependency and supercedes graphs.

        :param tasks: Tasks to process
        :type tasks: TaskDictCollection
        :return: Processed tasks with resolved enable/disable states
        :rtype: TaskDictCollection
        """
        # Enable all dependencies of enabled tasks if enable_dependencies is set
        if self.enable_dependencies:
            for node in nx.topological_sort(self._dependency_graph):
                if tasks[node]["enabled"]:
                    for dep in nx.ancestors(self._dependency_graph, node):
                        if not tasks[dep]["enabled"]:
                            tasks[dep]["enabled"] = True
                            self.logger.info(
                                f"Enabling dependency '{dep}' "
                                f"because '{node}' is enabled "
                                "and enable_dependencies=True"
                            )

        def _graph_pass(graph: nx.DiGraph, is_dependency_graph: bool) -> bool:
            """
            Single pass over the given graph to enable/disable tasks.

            :param graph: Graph to process
            :type graph: nx.DiGraph
            :param is_dependency_graph: Whether the graph is a dependency graph (True) or a supercedes graph (False)
            :type is_dependency_graph: bool
            """
            _changed = False
            for node in nx.topological_sort(graph):
                if tasks[node]["enabled"]:
                    predecessors = list(graph.predecessors(node))
                    relevant_predecessors = [
                        p
                        for p in predecessors
                        if tasks[p]["enabled"] != is_dependency_graph
                    ]
                    if relevant_predecessors:
                        _changed = True
                        tasks[node]["enabled"] = False
                        self.logger.warning(
                            f"Task '{node}' was disabled because of "
                            f"{'disabled dependencies' if is_dependency_graph else 'enabled superceders'}"
                            f": {relevant_predecessors}"
                        )
            return _changed

        # Repeatedly apply dependency and supercedes rules until no changes occur
        changed = True
        while changed:
            changed = False
            changed |= _graph_pass(self._dependency_graph, True)
            changed |= _graph_pass(self._supercedes_graph, False)

        self.logger.debug(
            "Resolved dependency and supercedes enabling/disabling"
        )
        return tasks
