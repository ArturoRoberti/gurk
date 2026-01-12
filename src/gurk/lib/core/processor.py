from dataclasses import dataclass, field
from textwrap import dedent

import networkx as nx

from gurk.lib.core.plugin_utils import get_combined_plugin_tasks
from gurk.lib.logger import get_logger
from gurk.lib.utils.cli import GurkArgumentParser
from gurk.lib.utils.common import generate_random_path
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
from gurk.lib.utils.yaml import overlay_dicts


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
        tasks = get_combined_plugin_tasks()

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

        # Filter only enabled tasks
        tasks = {
            task_name: task
            for task_name, task in tasks.items()
            if task["enabled"]
        }
        task_args = {
            task_name: task_args[task_name] for task_name in tasks.keys()
        }

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

        # If all args are good, re-insert them back
        for task_name, task in tasks.items():
            if not task["enabled"]:
                continue

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

        # Prepend system preparation task
        tasks = self.add_preparation_task(tasks)

        # Create logging directory
        logger.create_log_dir()

        # Convert to ResolvedTask list
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
            if tasks[node]["enabled"]:
                for dep in nx.ancestors(dependency_graph, node):
                    if not tasks[dep]["enabled"]:
                        tasks[dep]["enabled"] = True
                        logger.debug(f"Enabling dependency '{dep}'")

        return tasks

    def add_preparation_task(
        self, tasks: ResolvedTaskDictCollection
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

                    # (STEP) Upgrading apt packages...
                    sudo apt-get upgrade -y
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
            enabled=True,
        )

        # Prepend preparation task to all tasks' dependencies
        for _, task in tasks.items():
            task["depends_on"].insert(0, prepare_task_name)
        tasks[prepare_task_name] = prep_task

        return tasks
