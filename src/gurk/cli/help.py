from pathlib import Path

from gurk.plugin.utils import GurkPlugin, check_local_plugin, get_plugin_data
from gurk.utils.cli import CleanArgumentParser
from gurk.utils.yaml import load_yaml


def main(argv, prog, description):
    parser = CleanArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "plugins",
        type=str,
        nargs="+",
        help="Names of installed custom plugins to show help for",
    )
    args = parser.parse_args(argv)

    for plugin_name in args.plugins:
        # Get plugin data (if installed)
        plugin = get_plugin_data(plugin_name)
        if not plugin:
            print(f"Plugin '{plugin_name}' is not installed.")
            # TODO: Use logger (error)
            continue

        # Check that the plugin is valid
        try:
            check_local_plugin(plugin["local"])
        except SystemExit:
            print(
                f"Plugin '{plugin_name}' at {plugin['local']} has an invalid 'gurk-plugin.yaml' file."
            )
            # TODO: Use logger (error)
            continue

        # Get info from gurk-plugin.yaml - TODO: Outsource to helper
        plugin_yaml: GurkPlugin = load_yaml(
            Path(plugin["local"]) / "gurk-plugin.yaml"
        )
        if not plugin_yaml:
            print(
                f"Plugin '{plugin_name}' is missing a valid 'gurk-plugin.yaml' file."
            )
            # TODO: Use logger (error)
            continue

        # TODO: Indent the following properly

        # Print general info
        # Logger.richprint("======= General =======", color="cyan")
        print(
            "======= General ======="
        )  # TODO: Use logger.richprint instead. Also, use pytest helper for getting proper '====' lines.
        print(f"Name: {plugin_name}")
        print(f"Description: {plugin_yaml['define']['description']}")
        # print(f"Version: {plugin_yaml['define'].get('version', 'N/A')}")
        print(
            f"Source: {plugin['remote'] if plugin['remote'] else plugin['local']}"
        )

        # Print tasks defined by the plugin
        if "tasks" in plugin_yaml:
            print("======== Tasks ========")
            # TODO: Use common util with 'info' command for printing task fields
            for task_name, task_info in plugin_yaml["tasks"].items():
                print(f"- {task_name}: {task_info}")

        # Print imported plugins
        if "import" in plugin_yaml:
            print("====== Imports ======")
            for imported_plugin in plugin_yaml["import"]:
                print(f"- {imported_plugin}")

        # Print 'run' section
        if "run" in plugin_yaml:
            run_section = plugin_yaml["run"]

            # Print default
            print("======== Run ========")
            default_key, default_value = next(
                iter(run_section["default"].items())
            )
            print(
                f"- {plugin_name}={default_key + ' (default)'}: {default_value}"
            )

            options = run_section.get("options", {})
            options.pop(default_key, None)  # Remove default from options
            # old_default = run_section["default"]
            # old_default_name = next(iter(old_default))
            # new_default = {old_default_name + " (default)": old_default[old_default_name]}
            # options.update(new_default)
            for run_option, run_info in options.items():
                # TODO: Also use common task printing util for printing run tasks (these are custom tasks though)
                print(f"- {plugin_name}={run_option}: {run_info}")
