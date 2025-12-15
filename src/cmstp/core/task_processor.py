import textwrap
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import networkx as nx

from cmstp.core.logger import Logger
from cmstp.utils.command import Command, CommandKind
from cmstp.utils.common import PACKAGE_CONFIG_PATH
from cmstp.utils.patterns import PatternCollection
from cmstp.utils.tasks import (
    TASK_ARGS_DEFAULT,
    TASK_PROPERTIES_CUSTOM,
    TASK_PROPERTIES_DEFAULT,
    ResolvedTask,
    TaskDictCollection,
    get_invalid_tasks_from_task_dict_collection,
    print_expected_task_fields,
)
from cmstp.utils.yaml import load_yaml, overlay_dicts


# TODO: Extract (into funcs) and order tests, e.g. check structure, check script/function existence, check args, check dependencies, check supercedes, etc.
@dataclass
class TaskProcessor:
    """Processes tasks to run by resolving task properties."""

    # fmt: off
    logger:              Logger             = field(repr=False)
    config_file:         Optional[Path]     = field()
    config_directory:    Path               = field()
    custom_tasks:        List[str]          = field()
    enable_all:          Optional[bool]     = field()
    enable_dependencies: Optional[bool]     = field()

    resolved_tasks:      List[ResolvedTask] = field(init=False, repr=False, default=None)

    # Internal
    _default_config:  Path                  = field(init=False, repr=False, default=PACKAGE_CONFIG_PATH / "default.yaml")
    _allowed_args:    Dict[str, List[str]]  = field(init=False, repr=False, default_factory=dict)
    # fmt: on

    def __post_init__(self):
        # (Internal) Check default config file
        default_config = self.check_default_config()

        # Check custom config file
        if self.config_file is not None:
            custom_config = load_yaml(self.config_file)
            custom_config = self.check_config(custom_config)
        else:
            self.logger.debug(
                "Tasks have been specified directly and no config "
                "file is specified, so only those tasks will be run"
            )
            custom_config = {}

        # Check custom tasks
        custom_tasks = self.check_config(self.process_custom_tasks())

        # Merge default and custom config
        tasks = overlay_dicts(
            [default_config, custom_config, custom_tasks], allow_default=True
        )

        # Disable tasks in custom config that are not in default config
        for task_name in custom_config:
            if task_name not in default_config:
                self.logger.warning(
                    f"Task '{task_name}' in custom config is disabled "
                    f"because it is not defined in the default config"
                )
                tasks[task_name]["enabled"] = False

        # Fill in missing optional fields with defaults (including for default config)
        tasks = self.fill_missing_fields(tasks)

        # Resolve dependencies (disable tasks that depend on disabled ones)
        tasks = self.check_dependencies(tasks)

        # Handle conflicting/superceding tasks
        tasks = self.check_conflicts(tasks)

        # Prepend config directory to config file paths
        tasks = self.prepend_config_directory(tasks)

        # Count enabled tasks
        if self.count_tasks(tasks) == 0:
            self.logger.fatal(
                "There are no enabled tasks (anymore). Nothing to do"
            )
        else:
            self.logger.debug(
                f"Final enabled tasks: {[name for name, task in tasks.items() if task['enabled']]}"
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

    def prepend_config_directory(
        self, tasks: TaskDictCollection
    ) -> TaskDictCollection:
        # TODO: Move to better location, e.g. after overlay?
        """
        Prepend config directory to config file paths in tasks.

        :param tasks: Tasks to process
        :type tasks: TaskDictCollection
        :return: Processed tasks
        :rtype: TaskDictCollection
        """
        for task_name, task in tasks.items():
            if task["config_file"] is not None:
                config_file = (
                    self.config_directory / task["config_file"]
                ).resolve()

                if not config_file.exists():
                    self.logger.fatal(
                        f"Config file '{config_file}' for "
                        f"task '{task_name}' does not exist"
                    )
                else:
                    task["config_file"] = str(config_file)

        return tasks

    def fill_missing_fields(
        self,
        tasks: TaskDictCollection,
        include_default: bool = True,
        include_custom: bool = True,
    ) -> TaskDictCollection:
        """
        Fill in missing optional fields with defaults.

        :param tasks: Tasks to process
        :type tasks: TaskDictCollection
        :param enable_all: Whether to enable all tasks by default
        :type enable_all: bool
        :param include_default: Whether to include default tasks
        :type include_default: bool
        :param include_custom: Whether to include custom tasks
        :type include_custom: bool
        :return: Processed tasks with missing fields filled
        :rtype: TaskDictCollection
        """
        expected_properties = dict()
        expected_args = dict()
        if include_default:
            expected_properties |= TASK_PROPERTIES_DEFAULT
            expected_args |= TASK_ARGS_DEFAULT
        if include_custom:
            expected_properties |= TASK_PROPERTIES_CUSTOM
            expected_args = list()

        filled_tasks = deepcopy(tasks)
        for task_name, task in filled_tasks.items():
            task_disabled = False
            # Task properties
            for task_field, default in expected_properties.items():
                # NOTE: bool() = False
                called_default = (
                    default[0]() if callable(default[0]) else default[0]
                )
                if task_field not in task:
                    if task_field == "enabled":
                        if not task_disabled:
                            task[task_field] = (
                                self.enable_all
                                if self.enable_all is not None
                                else called_default
                            )
                        if task_name.startswith("uninstall"):
                            # Uninstall tasks are disabled by default for now - TODO: Change as soon as separate "uninstall" entrypoint is added
                            task[task_field] = False
                    elif task_field == "config_file":
                        task[task_field] = "default"
                    else:
                        task[task_field] = called_default
                else:
                    if not (
                        (None in default and task[task_field] is None)
                        or any(
                            isinstance(task[task_field], t)
                            for t in default
                            if t is not None
                        )
                    ):
                        self.logger.warning(
                            f"Disabling task '{task_name}' because task property '{task_field}' has incorrect "
                            f"type (expected: {default}, got: {type(task[task_field]).__name__})"
                        )
                        task[task_field] = called_default
                        task["enabled"] = False
                        task_disabled = True

            # Task args
            if "args" not in task:
                task["args"] = type(expected_args)()
            if isinstance(expected_args, list):
                if not isinstance(task["args"], list) or not all(
                    isinstance(arg, str) for arg in task["args"]
                ):
                    self.logger.warning(
                        f"Disabling task '{task_name}' because 'args' field is not a list of strings"
                    )
                    task["enabled"] = False
                    task["args"] = []
            elif isinstance(expected_args, dict):
                if not isinstance(task["args"], dict):
                    self.logger.warning(
                        f"Disabling task '{task_name}' because 'args' field is not a dict"
                    )
                    task["enabled"] = False
                    task["args"] = {}
                for arg_field, default in expected_args.items():
                    # NOTE: bool() = False
                    called_default = (
                        default[0]() if callable(default[0]) else default[0]
                    )
                    if arg_field not in task["args"]:
                        task["args"][arg_field] = called_default
                    else:
                        if not (
                            (
                                None in default
                                and task["args"][arg_field] is None
                            )
                            or any(
                                isinstance(task["args"][arg_field], t)
                                for t in default
                                if t is not None
                            )
                        ):
                            self.logger.warning(
                                f"Disabling task '{task_name}' because task arg '{arg_field}' has incorrect "
                                f"type (expected: {default}, got: {type(task['args'][arg_field]).__name__})"
                            )
                            task["args"][arg_field] = called_default
                            task["enabled"] = False

        return filled_tasks

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
                f"Error in default config file {self._default_config}: {f'{task_name}:' if task_name else ''} {msg}"
            )

        # Check file exists and is not empty
        default_config = load_yaml(self._default_config)
        if default_config is None:
            fatal("File does not exist or is not valid YAML")
        if not default_config:
            fatal("File is empty")
        if not isinstance(default_config, dict):
            fatal(
                "File does not define a dict, but a "
                + type(default_config).__name__
            )

        # Remove helpers (start with '_') that may otherwise be picked up as tasks
        defaults = default_config["_defaults"]
        default_config = {
            k: overlay_dicts([defaults, v])
            for k, v in default_config.items()
            if not k.startswith("_")
        }

        # Check structure (incl. types)
        invalid_tasks = get_invalid_tasks_from_task_dict_collection(
            default_config
        )
        if invalid_tasks:
            fatal_msg = textwrap.dedent(
                f"""\
                Some tasks have extra or missing fields, or use incorrect types: {invalid_tasks}
                [cyan]Required structure for tasks in the default config[/cyan]:
            """
            )
            fatal(
                fatal_msg
                + print_expected_task_fields(
                    TASK_PROPERTIES_DEFAULT, TASK_ARGS_DEFAULT
                )
            )

        # Check everything else
        existing_scripts = set()
        for task_name, task in default_config.items():
            # Check 'description' field
            if not task["description"]:
                fatal("Description is empty", task_name)

            # Check 'script' field
            if not task["script"]:
                fatal(
                    "Script is either null, empty or uses a package that can't be found",
                    task_name,
                )
            if not Path(task["script"]).exists():
                fatal(f"'{task['script']}' script does not exist", task_name)

            # Check for duplicate (script, function) pairs
            script_command = Command(task["script"], task["function"])
            if script_command in existing_scripts:
                fatal(
                    f"Duplicate (script, function) pair: {script_command}",
                    task_name,
                )
            else:
                existing_scripts.add(script_command)

            # Check 'function' field
            if task["function"] is not None:
                # Get script info
                script_kind = script_command.kind
                with open(task["script"]) as f:
                    lines = f.readlines()

                # Find function in script
                function_pattern = PatternCollection[
                    script_kind.name
                ].patterns["blocks"]["FUNCTION"]
                function_matches = [
                    match.groups()
                    for line in lines
                    if (match := function_pattern.search(line.strip()))
                ]
                if script_kind == CommandKind.PYTHON:  # Also capture args
                    function_names = [name for name, _ in function_matches]
                else:  # No args are captured in bash
                    function_names = [name for name, in function_matches]
                if task["function"] not in function_names:
                    fatal(
                        f"'{task['function']}' function not found in script "
                        f"{task['script']}\nAvailable functions: {function_names}",
                        task_name,
                    )

                # If Python, check function definition only captures '*args'
                elif script_kind == CommandKind.PYTHON:
                    # Test if the function has only *args
                    function_args = [args for _, args in function_matches]
                    args = function_args[
                        function_names.index(task["function"])
                    ]
                    arg_list = [
                        a.strip() for a in args.split(",") if a.strip()
                    ]
                    if not (
                        len(arg_list) == 1
                        and arg_list[0].split(":")[0] == "*args"
                    ):
                        fatal(
                            f"'{task['function']}' function in script "
                            f"{task['script']} must ONLY capture '*args' as "
                            f"an argument, if it is to be used as a task",
                            task_name,
                        )

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
            else:
                value = None
            if getattr(self, option) is None and value:
                if not isinstance(value, bool):
                    warning(
                        f"Ignoring '{option}' value - must be "
                        f"a boolean, not a {type(value).__name__}"
                    )
                    value = False
                setattr(self, option, value)

        # Check for "enable_all" parameter
        check_option("enable_all")

        # Check for "enable_dependencies" parameter
        check_option("enable_dependencies")

        # Add defaults for missing optional fields. Used to check structure of custom config tasks
        checked_custom_config = self.fill_missing_fields(
            config, include_default=False
        )

        # Check structure (incl. types)
        invalid_tasks = get_invalid_tasks_from_task_dict_collection(
            checked_custom_config, include_default=False, include_custom=True
        )
        if invalid_tasks:
            warning_msg = textwrap.dedent(
                f"""\
                Some tasks that have extra fields or are trying to override default fields are disabled: {invalid_tasks}
                [cyan]Required structure for tasks in the custom config[/cyan] (all fields optional):
            """
            )
            warning(
                warning_msg
                + print_expected_task_fields(TASK_PROPERTIES_CUSTOM)
            )
            for task in invalid_tasks:
                checked_custom_config[task]["enabled"] = False

        # Check args
        for task_name, task in checked_custom_config.items():
            # Check custom args are allowed
            wrong_args, is_allowed = self.check_allowed(
                self._allowed_args[task_name], task["args"]
            )
            if not is_allowed:
                warning(
                    f"Task '{task_name}' was disabled because some custom "
                    f"args ({wrong_args}) are not in allowed args "
                    f"{self._allowed_args[task_name]}"
                )
                task["enabled"] = False

        self.logger.debug("Config is valid")
        return checked_custom_config

    def process_custom_tasks(self) -> TaskDictCollection:
        """
        Process custom tasks specified in the command line (e.g. `task_name:arg1:arg2:...`).

        :return: Processed custom config tasks
        :rtype: TaskDictCollection
        """
        processed_tasks = dict()
        for task_str in self.custom_tasks:
            parts = task_str.split(":")
            task_name = parts[0]
            task_args = parts[1:] if len(parts) > 1 else []

            processed_tasks[task_name] = {"enabled": True}
            if task_args:
                processed_tasks[task_name]["args"] = task_args

                # Check custom args
                wrong_args, is_allowed = self.check_allowed(
                    self._allowed_args.get(task_name, []), task_args
                )
                if not is_allowed:
                    self.logger.warning(
                        f"Task '{task_name}' was disabled because some custom "
                        f"args ({wrong_args}) are not in allowed args "
                        f"{self._allowed_args.get(task_name, [])}"
                    )
                    processed_tasks[task_name]["enabled"] = False

        if not processed_tasks:
            self.logger.debug("No custom tasks were specified")

        return processed_tasks

    @staticmethod
    def check_allowed(
        allowed_args: Optional[List[str]], args: Union[str, List[str]]
    ) -> Tuple[List[str], bool]:
        """
        Check if an argument is in the allowed list.
        If allowed_args is None, any argument is allowed.

        :param allowed_args: List of allowed arguments or None if any argument is allowed
        :type allowed_args: Optional[List[str]]
        :param args: Argument or list of arguments to check
        :type args: Union[str, List[str]]
        :return: Tuple of (list of wrong arguments, is valid)
        :rtype: Tuple[List[str], bool]
        """

        def _check_single_allowed(allowed_args: List[str], arg: str) -> bool:
            """
            Check if a single argument is allowed, supporting wildcard '*'

            :param allowed_args: List of allowed arguments
            :type allowed_args: List[str]
            :param arg: Argument to check
            :type arg: str
            :return: Whether the argument is allowed
            :rtype: bool
            """
            for allowed in allowed_args:
                if allowed.endswith("*"):
                    if arg.startswith(allowed[:-1]):
                        return True
                elif arg == allowed:
                    return True
            return False

        if allowed_args is None:
            return [], True
        if isinstance(args, str):
            is_allowed = _check_single_allowed(allowed_args, args)
            wrong_args = [] if is_allowed else [args]
            return wrong_args, is_allowed
        else:  # List[str]
            wrong_args = [
                arg
                for arg in args
                if not _check_single_allowed(allowed_args, arg)
            ]
            return wrong_args, not wrong_args

    def check_dependencies(
        self, tasks: TaskDictCollection
    ) -> TaskDictCollection:
        """
        Check task dependencies and enable/disable tasks accordingly. Specifically:
        1. Ensures all dependencies exist
        2. Raises fatal error if dependency graph has cycles
        3. If `self.enable_dependencies` is True:
           Enables all dependencies of enabled tasks (recursively)
        4. Otherwise:
           Disables any task whose dependencies are disabled

        :param tasks: Tasks to process
        :type tasks: TaskDictCollection
        :return: Processed tasks with checked dependencies
        :rtype: TaskDictCollection
        """
        # Build dependency graph
        G = nx.DiGraph()
        for task_name, task in tasks.items():
            G.add_node(task_name)
            for dep in task["depends_on"]:
                if dep not in tasks:
                    self.logger.fatal(
                        f"Dependency '{dep}' for '{task_name}' "
                        f"not found - needs to be defined in config"
                    )
                G.add_edge(dep, task_name)

        # Check for cycles
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            self.logger.fatal(f"Dependency graph has cycles between: {cycles}")

        # Topological resolution
        for node in nx.topological_sort(G):
            task = tasks[node]

            if self.enable_dependencies:
                # Recursively enable dependencies
                if task["enabled"]:
                    # Recursively enable all dependencies of this enabled task
                    for dep in nx.ancestors(G, node):
                        if not tasks[dep]["enabled"]:
                            tasks[dep]["enabled"] = True
                            self.logger.info(
                                f"Enabling dependency '{dep}' "
                                f"because '{node}' is enabled and enable_dependencies=True"
                            )

            else:
                if not task["enabled"]:
                    continue
                # Disable task if any dependencies are disabled
                deps = list(G.predecessors(node))
                disabled_deps = [d for d in deps if not tasks[d]["enabled"]]
                if disabled_deps:
                    task["enabled"] = False
                    self.logger.warning(
                        f"Task '{node}' was disabled because it depends on "
                        f"disabled tasks: {disabled_deps}"
                    )

        self.logger.debug("Checked task dependencies")
        return tasks

    def check_conflicts(self, tasks: TaskDictCollection) -> TaskDictCollection:
        """
        Disable tasks that are conflicting with superceding tasks.

        :param tasks: Tasks to process
        :type tasks: TaskDictCollection
        :return: Processed tasks with checked conflicts
        :rtype: TaskDictCollection
        """
        # First, collect all tasks that are enabled and have 'supercedes' field
        superceding_tasks = {
            task_name: task
            for task_name, task in tasks.items()
            if task["enabled"] and task["supercedes"] is not None
        }

        # Disable conflicting tasks
        for task_name, task in superceding_tasks.items():
            for conflicted_task in task["supercedes"]:
                if tasks[conflicted_task]["enabled"]:
                    tasks[conflicted_task]["enabled"] = False
                    self.logger.debug(
                        f"Disabling task '{conflicted_task}' because it "
                        f"conflicts with superceding task '{task_name}'"
                    )

        self.logger.debug("Checked for conflicting/superceding tasks")
        return tasks

    @staticmethod
    def count_tasks(tasks: TaskDictCollection) -> int:
        """
        Count the number of enabled tasks.

        :param tasks: Tasks to count
        :type tasks: TaskDictCollection
        :return: Number of enabled tasks
        :rtype: int
        """
        count = 0
        for task in tasks.values():
            if task.get("enabled", False):
                count += 1
        return count
