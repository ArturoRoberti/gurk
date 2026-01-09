from argparse import ArgumentTypeError
from pathlib import Path

from ruamel.yaml import YAML

from gurk.cli import core
from gurk.plugin.utils import (
    GurkPlugin,
    check_local_plugin,
    get_plugin_data,
    import_plugin,
)
from gurk.utils.cli import CleanArgumentParser
from gurk.utils.common import generate_random_path
from gurk.utils.yaml import load_yaml


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
    parser = CleanArgumentParser(prog=prog, description=description)

    # Add required arguments
    required = parser.add_required_group()
    group = required.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--plugin",
        type=str,
        help="Name of the plugin to run",
    )
    group.add_argument(
        "--task",
        type=parse_task,
        help="Specify a task to run as 'plugin_name/task_name'",
    )

    # Add options
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update the plugin if it is already installed",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "-y",
        "--yes",
        "--non-interactive",
        dest="non_interactive",
        action="store_true",
        help="IAutomatically answer 'yes' to or ignore all prompts",
    )
    args = parser.parse_args(argv)

    plugin_name, option_spec = (args.plugin.split("=", 1) + [None])[:2]

    # Get plugin data
    plugin = get_plugin_data(plugin_name)
    if not plugin or args.update:
        # Import plugin
        if not import_plugin(args.plugin, args.update):
            print(f"Failed to import plugin '{args.plugin}'.")
            # TODO: Use logger (fatal)
            return

        plugin = get_plugin_data(plugin_name)
        if not plugin:
            # Safety check, should not happen
            print(f"Plugin '{plugin_name}' is not installed after import.")
            # TODO: Use logger (fatal)
            return

    # Check validity of plugin - TODO: require_local might not be necessary if import is recursive
    if not check_local_plugin(plugin["local"], True, True):
        print(
            f"Plugin '{plugin_name}' at {plugin['local']} has a 'gurk-plugin.yaml' file that is either invalid or imports non-local plugins."
        )
        # TODO: Use logger (fatal)
        return

    # Get info from gurk-plugin.yaml
    plugin_yaml: GurkPlugin = load_yaml(
        Path(plugin["local"]) / "gurk-plugin.yaml"
    )
    if not plugin_yaml:
        print(
            f"Plugin '{plugin_name}' is missing a valid 'gurk-plugin.yaml' file."
        )
        # TODO: Use logger (error)
        return

    # Get option task(s)
    option = (
        plugin_yaml["run"].get("default")
        if option_spec is None
        else plugin_yaml["run"]["options"].get(option_spec)
    )
    if not option:
        print(
            f"Plugin '{plugin_name}' does not have a run option specified for '{option_spec}'. Available options are: {list(plugin_yaml['run']['options'].keys())} (or default)."
        )
        # TODO: Use logger (error)
        return

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
