from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from gurk.cli import core
from gurk.cli.utils import CORE_COMMANDS
from gurk.plugin.utils import (
    GurkPlugin,
    check_local_plugin,
    get_plugin_data,
    import_plugin,
)
from gurk.utils.common import generate_random_path
from gurk.utils.yaml import load_yaml


# TODO: Is it possible to get flags from core here dynamically?
@dataclass
class RunArgs:
    # fmt: off
    plugin:              str  = field(metadata={"help": "Name or git URL of the plugin to run. Specify option via '=<option>' suffix to select non-default task set."})
    update:              bool = field(metadata={"help": "Update the plugin if it is already installed"}, default=False)
    enable_dependencies: bool = field(metadata={"help": "Same flag as '--enable-dependencies' in 'gurk <core command>'"}, default=False)
    enable_all:          bool = field(metadata={"help": "Same flag as '--enable-all' in 'gurk <core command>'"}, default=False)
    verbose:             bool = field(metadata={"help": "Same flag as '-v/--verbose' in 'gurk <core command>'"}, default=False)
    disable_preparation: bool = field(metadata={"help": "Same flag as '--disable-preparation' in 'gurk <core command>'"}, default=False)
    yes:                 bool = field(metadata={"help": "Same flag as '-y/--yes' in 'gurk <core command>'"}, default=False)
    # fmt: on


def run_cmd(args: RunArgs) -> None:
    """
    Docstring for run_cmd

    :param args: Description
    :type args: RunArgs
    """
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

    # Infer command from first defined task
    command = next(iter(option)).split("-", 1)[0]
    if command not in CORE_COMMANDS:
        print(
            f"Plugin '{plugin_name}' has an invalid command '{command}' in its run option '{option_spec or 'default'}'. Supported commands are: {CORE_COMMANDS}."
        )

    # Run task(s)
    core.main(
        argv=["-f", str(tmp_yaml)],
        prog="",
        description="",
        cmd="install",  # TODO: !!! Allow other commands? How to specify them? Maybe take it from the first task?
    )
