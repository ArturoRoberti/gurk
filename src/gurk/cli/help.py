from pprint import pprint

from rich import print as richprint

from gurk.lib.core.plugin_utils import (
    GurkArgumentParser,
    get_plugin_data,
    get_plugin_entry,
)
from gurk.lib.logger import ActiveLogger, Logger


# TODO: Restructure to
#       - `gurk help --plugin <plugin_name>` for specific plugin help (current implementation)
#       - `gurk help --task <plugin_name/task_name>` for specific task help
#       - `gurk help --available-plugins` to list all installed plugins with brief info
#       - `gurk help --available-tasks` to list all available tasks from all installed plugins
#       - `gurk help --system-info` to print system info (current `gurk info --system-info`)
#       - `gurk help` to print help about gurk itself
# TODO: Restructure so that current implementation is called with `gurk help --plugin <plugin_name>`
#       Then add similar help for --task
def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "plugins",
        type=str,
        nargs="+",
        help="Names of installed custom plugins to show help for",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        for plugin_name in args.plugins:
            # Get plugin (if installed)
            plugin_entry, plugin_yaml, plugin_metadata = get_plugin_data(
                plugin_name
            )
            if not plugin_entry or not plugin_yaml or not plugin_metadata:
                logger.error(
                    f"Plugin '{plugin_name}' is not installed or has an invalid 'gurk-plugin.yaml' file."
                )
                continue

            # Re-get plugin name from metadata if available, in case another PluginSpec was used
            plugin_name = plugin_metadata["name"]

            # Print general info
            logger.padded_print(
                f"Plugin '{plugin_name}' General Info", "green"
            )
            richprint(f"[yellow]Name        :[/yellow] {plugin_name}")
            richprint(
                f"[yellow]Version     :[/yellow] {plugin_metadata['version']}"
            )
            richprint(
                f"[yellow]Description :[/yellow] {plugin_metadata['description']}"
            )
            source = (
                plugin_entry["remote"]
                if plugin_entry["remote"]
                else plugin_entry["local"]
            )
            richprint(f"[yellow]Source      :[/yellow] {source}")
            dependencies = plugin_metadata["dependencies"]
            if dependencies:
                richprint(f"[yellow]Dependencies: {dependencies}[/yellow]")
            print()

            # Print tasks defined by the plugin
            if plugin_yaml.get("tasks"):
                logger.padded_print("Defined Tasks", "cyan")
                for task_name, task_info in plugin_yaml["tasks"].items():
                    logger.richprint(f"- {task_name}:", "yellow")
                    pprint(task_info)
                    print()

            # Print imported plugins
            if plugin_yaml.get("imports"):
                logger.padded_print("Imported Plugins", "cyan")
                for imported_plugin in plugin_yaml["imports"]:
                    plugin_entry = get_plugin_entry(imported_plugin)
                    print(
                        f"- {imported_plugin}: {plugin_entry['remote'] if plugin_entry['remote'] else plugin_entry['local']}"
                    )
                print()

            # Print 'run' section
            run_section = plugin_yaml["run"]
            ## Print default
            logger.padded_print("Run Options", "cyan")
            default_value = next(iter(run_section["default"].values()))
            logger.richprint(f"- {plugin_name} (default):", "green")
            pprint(default_value)
            print()
            ## Print other options
            if run_section.get("options"):
                options = run_section.get("options", {})
                for run_option, run_info in options.items():
                    logger.richprint(
                        f"- {plugin_name}={run_option}: ", "yellow"
                    )
                    pprint(run_info)
                    print()
