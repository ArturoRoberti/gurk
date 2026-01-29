from argparse import ArgumentTypeError

from gurk.lib.core import core
from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import (
    GurkArgumentParser,
    check_local_plugin,
    get_plugin_data,
    installed_plugin_path,
    load_raw_plugin_manifest,
    pull_plugin,
)
from gurk.lib.utils.remotes import is_git_repo
from gurk.lib.utils.tasks import COMMON_RESOLVED_TASK_DICT_FIELDS


def split_argv_at_plugin_task(argv: list[str]) -> tuple[list[str], list[str]]:
    """
    Split argv into base args and plugin/task specific args.

    :param argv: The full argument list.
    :type argv: list[str]
    :return: A tuple (run_argv, remaining).
    :rtype: tuple[list[str], list[str]]
    """
    for i, arg in enumerate(argv):
        if arg in ("-p", "--plugin", "-t", "--task"):
            # include the name following --plugin/--task in base argv
            return argv[: i + 2], argv[i + 2 :]
    return argv, []


def parse_task(value: str) -> tuple[str, str]:
    """
    Parse --task argument in the form 'plugin_name/task_name'.

    :param value: The input string to parse.
    :type value: str
    :return: A tuple (plugin_name, task_name).
    :rtype: tuple[str, str]
    :raises ArgumentTypeError: If the input format is invalid.
    """
    parts = value.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ArgumentTypeError(
            f"Invalid task format: {value!r}. Expected 'plugin_name/task_name'"
        )
    return tuple(parts)  # (plugin_name, task_name)


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)

    # Add required arguments
    group = parser.add_required_group(mutex=True)
    group.add_argument(
        "-p",
        "--plugin",
        type=str,
        help="PluginSpec (name, local path or remote) of the plugin to run",
    )
    group.add_argument(
        "-t",
        "--task",
        type=parse_task,
        help="Specify an installed task to run as 'plugin_name/task_name'",
    )

    # Only parse 'run' specific args, keep the rest for later
    run_argv, remaining = split_argv_at_plugin_task(argv)
    args = parser.parse_args(run_argv)

    # Determine if running a plugin or task
    if args.plugin:
        plugin = args.plugin
        task_name = None
    else:
        plugin, task_name = args.task

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        plugin_name, option_spec = (plugin.split("=", 1) + [None])[:2]
        if option_spec is None:
            option_spec = "default"

        # Get plugin data
        try:
            plugin_data = get_plugin_data(plugin_name)
        except ModuleNotFoundError:
            # Plugin is installed, but invalid
            plugin_local = installed_plugin_path(plugin)
            if plugin_local:
                check_local_plugin(plugin_local, True)
                logger.fatal(
                    f"Plugin '{plugin_name}' is installed but invalid. Please fix or remove it via 'gurk remove {plugin_name}'."
                )

            # Plugin is not installed
            msg = f"Plugin '{plugin_name}' is not installed."
            if not is_git_repo(plugin):
                # Local-only plugin, cannot pull
                logger.fatal(
                    f"{msg} Please use its remote URL to run it via 'gurk run <plugin-remote>'."
                )
            else:
                # Attempt to pull
                logger.info(f"{msg} Pulling...")
                if not pull_plugin(plugin):
                    logger.fatal(f"Failed to pull plugin '{plugin}'.")

                # Get plugin data again after pulling
                try:
                    plugin_data = get_plugin_data(plugin_name)
                except ModuleNotFoundError as e:
                    logger.fatal(
                        f"Plugin '{plugin_name}' is still not installed after pulling: {str(e)}"
                    )

        if task_name:
            # Run a specific task
            run_type = "task"
            full_task_name = f"{plugin_name}/{task_name}"

            # Check that the task exists in the plugin
            plugin_tasks = plugin_data["manifest"]["tasks"]
            if full_task_name not in plugin_tasks:
                logger.fatal(
                    f"Plugin '{plugin_name}' does not have a task named '{full_task_name}'. "
                    f"Available tasks are: {list(plugin_tasks.keys())}."
                )

            # Define mock option with the specific task enabled
            option = {full_task_name: {"enabled": True}}
        else:
            # Run the plugin default or specified option
            run_type = "plugin"

            # Get option task(s)
            manifest_options = plugin_data["manifest"]["options"]
            option = manifest_options.get(option_spec)
            if not option:
                logger.fatal(
                    f"Plugin '{plugin_name}' does not have a run option specified for '{option_spec}'. "
                    f"Available options are: {list(manifest_options.keys())}."
                )

            # For any common fields, if they are missing in the raw option, remove them (to be filled later) to use defaults
            raw_plugin_yaml = load_raw_plugin_manifest(plugin_name)
            raw_option = raw_plugin_yaml["options"][option_spec]
            for (_, task), raw_task in zip(
                option.items(), raw_option.values()
            ):
                for field in COMMON_RESOLVED_TASK_DICT_FIELDS:
                    if field not in raw_task and field in task:
                        del task[field]

        # Generate task argparser base
        task_parser_base = GurkArgumentParser(
            prog=f"{prog} --{run_type} {task_name or plugin}",
            description=f"Options to run {task_name or plugin}",
            add_verbose_arg=False,
            add_non_interactive_arg=False,
            add_force_arg=True,
            add_task_args=False,
            allow_complex_types=False,
        )

        # Run task(s)
        core.main(
            option=option,
            cli_args=remaining,
            parser_base=task_parser_base,
        )

        # Final message
        logger.done(
            "All tasks completed - You may need to "
            "reboot for some changes to take effect"
        )
