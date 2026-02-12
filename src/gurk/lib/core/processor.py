from dataclasses import dataclass, field
from textwrap import dedent

import networkx as nx

from gurk.lib.core.context import get_logger
from gurk.lib.core.plugins import (
    GurkArgumentParser,
    get_available_plugin_tasks,
)
from gurk.lib.utils.common import PACKAGE_VENVS_PATH, generate_random_path
from gurk.lib.utils.configs import overlay_dicts
from gurk.lib.utils.scripts import Command
from gurk.lib.utils.tasks import (
    CustomTaskDictCollection,
    ResolvedArgsDefinitionCollection,
    ResolvedTask,
    ResolvedTaskDict,
    ResolvedTaskDictCollection,
    TaskDictCollection,
)
from gurk.lib.utils.typed_dict import fill_typed_dict


@dataclass
class Processor:
    """Class to process tasks based on provided options and CLI arguments."""

    # fmt: off
    option:      CustomTaskDictCollection = field()
    cli_args:    list[str]                = field()
    parser_base: GurkArgumentParser       = field()
    tasks:       list[ResolvedTask]       = field(init=False, default_factory=list)
    # fmt: on

    def __post_init__(self):
        # Get logger
        logger = get_logger()

        # Get all tasks
        tasks = get_available_plugin_tasks()

        # Extract task args
        task_args: ResolvedArgsDefinitionCollection = dict()
        for task_name, task in tasks.items():
            task_args[task_name] = task.pop("args")

        # Overlay option
        tasks = overlay_dicts([tasks, self.option])

        # Fill missing properties
        tasks = fill_typed_dict(tasks, ResolvedTaskDictCollection)

        # Enable dependencies of enabled tasks
        tasks = self.enable_dependencies(tasks)

        # Disable tasks whose venvs do not exist
        for task_name, task in tasks.items():
            plugin = task_name.split("/")[0]
            if (
                plugin != "gurk"
                and task_name in self.option
                and not (PACKAGE_VENVS_PATH / plugin).exists()
            ):
                del self.option[task_name]
                logger.warning(
                    f"Disabling task '{task_name}' as its plugin venv "
                    "does not exist. Did you forget to run 'gurk init'?"
                )

        # Filter only enabled tasks
        tasks = {
            task_name: task
            for task_name, task in tasks.items()
            if task_name in self.option
        }
        task_args = {
            task_name: task_args[task_name] for task_name in tasks.keys()
        }
        logger.debug(f"Enabled tasks: {list(tasks.keys())}")

        # Extract run args
        run_args = dict()
        for task_name, task in self.option.items():
            run_args[task_name] = self.option.pop("args", [])

        # Create argparser, removing args already passed in option
        for task_name, args in task_args.items():
            if args:
                used_args = set(args.keys()) & set(
                    self.option.get("args", {}).keys()
                )
                unused_args = {
                    arg_name: args[arg_name]
                    for arg_name in args.keys()
                    if arg_name not in used_args
                }
                self.parser_base.extend_arguments(unused_args)

        # Parse cli args
        parsed_cli_args = self.parser_base.parse_args(self.cli_args)
        logger.debug("Parsed CLI args successfully")

        # If all args are good, re-insert them back
        for task_name, task in tasks.items():
            task["args"] = []

            # Re-assign run args, if any
            if task_name in run_args:
                task["args"].extend(run_args[task_name])

            # Extend with always-allowed args, if any
            if {"-f", "--force"} & set(self.cli_args):
                task["args"].append("--force")

            # Extend with cli args that belong to this task, if any
            common_arg_names = set(task_args[task_name].keys()) & set(
                self.cli_args
            )
            common_args = []
            for arg in task_args[task_name].keys():
                if arg not in common_arg_names:
                    continue

                arg_attr = arg.lstrip("-").replace("-", "_")
                value = getattr(parsed_cli_args, arg_attr)

                common_args.append(arg)
                if isinstance(value, bool):
                    # Already appended
                    pass
                elif isinstance(value, str):
                    common_args.append(value)
                elif isinstance(value, list):
                    for v in value:
                        common_args.append(v)

            task["args"].extend(common_args)

        logger.debug("Assigned args to resp. tasks successfully")

        # Prepend system preparation task
        tasks = self.add_preparation_task(tasks)

        # Convert to ResolvedTask list
        for task_name, task in tasks.items():
            if task_name not in self.option:
                continue

            resolved_task = ResolvedTask(
                name=task_name,
                command=Command(task["script"], task["function"]),
                config_file=str(task["config_file"])
                if task["config_file"]
                else None,
                depends_on=tuple(task["depends_on"]),
                privileged=task["privileged"],
                args=tuple(task["args"]),
            )
            self.tasks.append(resolved_task)

    def enable_dependencies(
        self, tasks: TaskDictCollection
    ) -> TaskDictCollection:
        """
        Enable dependencies of enabled tasks.

        :param tasks: Tasks to process
        :type tasks: TaskDictCollection
        :return: Processed tasks with dependencies enabled
        :rtype: TaskDictCollection
        """
        # Get logger
        logger = get_logger()

        # Build dependency graph
        dependency_graph = nx.DiGraph()
        for task_name, task in tasks.items():
            dependency_graph.add_node(task_name)
            for dep in task["depends_on"]:
                dependency_graph.add_edge(dep, task_name)

        # Enable dependencies of enabled tasks
        for node in nx.topological_sort(dependency_graph):
            if node in self.option:
                for dep in nx.ancestors(dependency_graph, node):
                    if dep not in self.option:
                        self.option[dep] = {}
                        logger.debug(f"Enabling dependency '{dep}'")

        return tasks

    def add_preparation_task(
        self,
        tasks: ResolvedTaskDictCollection,
    ) -> ResolvedTaskDictCollection:
        """
        Prepend a system preparation task to update and upgrade apt packages.

        :param tasks: Tasks to process
        :type tasks: ResolvedTaskDictCollection
        :return: Processed tasks with preparation task added
        :rtype: ResolvedTaskDictCollection
        """
        prepare_task_name = "gurk/prepare-system"
        safe_task_name = prepare_task_name.replace("/", "-")

        # Create temporary bash script for preparation task
        tmp_path = generate_random_path(suffix=f"{safe_task_name}.bash")
        with open(tmp_path, "w") as f:
            f.write(
                dedent(
                    """\
                if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
                    # (STEP) Updating apt packages...
                    sudo apt-get update -y
                fi
                """
                )
            )

        # Define preparation task
        prep_task = ResolvedTaskDict(
            description="Prepare system by updating and upgrading apt packages",
            script=tmp_path,
            function=None,
            config_file=None,
            depends_on=[],
            privileged=False,
            supercedes=[],
            args=[],
        )

        # Enable prep task
        self.option[prepare_task_name] = {}

        # Prepend preparation task to all tasks' dependencies
        for _, task in tasks.items():
            task["depends_on"].insert(0, prepare_task_name)
        tasks[prepare_task_name] = prep_task

        return tasks
