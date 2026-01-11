from argparse import ArgumentTypeError

from ruamel.yaml import YAML

from gurk.lib.core import core
from gurk.lib.core.plugin_utils import (
    get_plugin_entry,
    load_resolved_plugin_yaml,
    pull_plugin,
)
from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.cli import GurkArgumentParser
from gurk.lib.utils.common import generate_random_path


def parse_task(value: str) -> tuple[str, str]:
    """
    Parse --task argument in the form 'plugin_name/task_name'.

    :param value: The input string to parse.
    :type value: str
    :return: A tuple (plugin_name, task_name).
    :rtype: tuple[str, str]
    :raises ArgumentTypeError: If the input format is invalid. # TODO: Add 'raises' to all funcs which raise smth
    """
    parts = value.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ArgumentTypeError(
            f"Invalid task format: {value!r}. Expected 'plugin_name/task_name'"
        )
    return tuple(parts)  # (plugin_name, task_name)


# TODO: Is it possible to get flags from core here dynamically?
def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)

    # Add required arguments
    required = parser.add_required_group()
    group = required.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--plugin",
        type=str,
        help="Name of the installed plugin to run",
    )
    group.add_argument(
        "--task",
        type=parse_task,
        help="Specify a task to run as 'plugin_name/task_name'",
    )

    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose)
    with ActiveLogger(logger):
        plugin_name, option_spec = (args.plugin.split("=", 1) + [None])[:2]

        # Import plugin if not installed
        plugin_entry = get_plugin_entry(plugin_name)
        if not plugin_entry and not pull_plugin(args.plugin):
            logger.fatal(f"Failed to import plugin '{args.plugin}'.")

        # Get plugin yaml
        plugin_yaml = load_resolved_plugin_yaml(plugin_name)
        if not plugin_yaml:
            logger.fatal(
                f"Plugin '{plugin_name}' is missing a valid 'gurk-plugin.yaml' file."
            )

        # Get option task(s)
        option = (
            plugin_yaml["run"]["default"]
            if option_spec is None
            else plugin_yaml["run"]["options"].get(option_spec)
        )
        if not option:
            logger.fatal(
                f"Plugin '{plugin_name}' does not have a run option specified for '{option_spec}'. "
                f"Available options are: {list(plugin_yaml['run']['options'].keys())} (or default)."
            )

        # Generate mock custom config file
        tmp_yaml = generate_random_path(suffix=".yaml")
        with open(tmp_yaml, "w") as f:
            YAML().dump(option, f)

        # Run task(s)
        core.main(
            argv=["-f", str(tmp_yaml)],
            prog="",
            description="",
            cmd="install",  # TODO: Remove
        )
