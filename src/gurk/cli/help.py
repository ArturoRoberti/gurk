from pprint import pprint

from rich import print as richprint

from gurk.lib.core.plugin_utils import (
    ResolvedGurkPlugin,
    get_plugin_entry,
    load_resolved_plugin_yaml,
)
from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.cli import GurkArgumentParser


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
            # Get plugin entry (if installed)
            plugin = get_plugin_entry(plugin_name)
            if not plugin:
                logger.error(f"Plugin '{plugin_name}' is not installed.")
                continue

            # Get plugin yaml
            plugin_yaml: ResolvedGurkPlugin = load_resolved_plugin_yaml(
                plugin_name
            )
            if not plugin_yaml:
                logger.error(
                    f"Plugin '{plugin_name}' is missing a valid 'gurk-plugin.yaml' file."
                )
                continue

            # Print general info
            logger.padded_print(
                f"Plugin '{plugin_name}' General Info", "green"
            )
            richprint(f"[yellow]Name       :[/yellow] {plugin_name}")
            richprint(
                f"[yellow]Description:[/yellow] {plugin_yaml['define']['description']}"
            )
            source = plugin["remote"] if plugin["remote"] else plugin["local"]
            richprint(f"[yellow]Source     :[/yellow] {source}\n")

            # Print tasks defined by the plugin
            if plugin_yaml["define"].get("tasks"):
                logger.padded_print("Defined Tasks", "cyan")
                for task_name, task_info in plugin_yaml["define"][
                    "tasks"
                ].items():
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
