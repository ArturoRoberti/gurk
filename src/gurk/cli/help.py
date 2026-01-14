from collections import defaultdict
from copy import deepcopy
from pprint import pprint

import toml

from gurk.lib.core.plugin_utils import (
    GurkArgumentParser,
    Plugin,
    PluginMetadata,
    get_combined_plugin_registry,
    get_combined_plugin_tasks,
    get_plugin_data,
    get_plugin_entry,
)
from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.common import PACKAGE_SRC_PATH
from gurk.lib.utils.system_info import get_system_info
from gurk.lib.utils.typed_dict import print_typed_dict_types


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-p",
        "--plugins",
        type=str,
        nargs="+",
        help="Names of installed plugins to show help for",
    )
    group.add_argument(
        "-t",
        "--tasks",
        type=str,
        nargs="+",
        help="Names of installed tasks to show help for",
    )
    group.add_argument(
        "--available-plugins",
        action="store_true",
        help="List installed plugins",
    )
    group.add_argument(
        "--available-tasks",
        action="store_true",
        help="List installed tasks",
    )
    group.add_argument(
        "--structure",
        action="store_true",
        help="Show the required structure of a plugin",
    )
    group.add_argument(
        "-s",
        "--system-info",
        action="store_true",
        help="Print system information",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        # Print help about gurk itself
        if not (
            args.plugins
            or args.tasks
            or args.available_plugins
            or args.available_tasks
            or args.system_info
            or args.structure
        ):
            # Load help from pyproject.toml
            gurk_toml = toml.load(
                PACKAGE_SRC_PATH.parents[1] / "pyproject.toml"
            )

            # Dictionary linking to gurk help
            gurk_help = {
                "Documentation": PACKAGE_SRC_PATH.parents[1]
                / "docs"
                / "knowledge",
                "Homepage": gurk_toml["project"]["urls"]["Homepage"],
            }

            # Link to documentation
            logger.richprint(
                "For detailed help, visit the Gurk documentation:", "green"
            )
            logger.pprint_simple_dict(gurk_help, color="yellow", indent=2)

        # Show help for specific plugins
        elif args.plugins:
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
                general_info = deepcopy(plugin_metadata)
                general_info["source"] = (
                    plugin_entry["remote"]
                    if plugin_entry["remote"]
                    else plugin_entry["local"]
                )
                logger.pprint_simple_dict(
                    general_info, color="yellow", capitalize=True
                )
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

        # Show help for specific tasks
        elif args.tasks:
            # Get all available tasks
            tasks = get_combined_plugin_tasks()
            logger.padded_print("Task Information", "cyan")

            for task_full_name in args.tasks:
                # Get task (if installed)
                task_info = tasks.get(task_full_name)
                if not task_info:
                    logger.error(f"Task '{task_full_name}' is not installed.")
                    continue

                # Print task info
                logger.richprint(f"Task '{task_full_name}':", "green")
                logger.pprint_simple_dict(
                    task_info, color="yellow", capitalize=True, indent=2
                )
                print()

        # Show available plugins
        elif args.available_plugins:
            logger.padded_print("Available Plugins", "cyan")
            combined_registry = get_combined_plugin_registry()
            for plugin_name, plugin_info in combined_registry.items():
                logger.richprint(f"{plugin_name}:", "green")
                logger.pprint_simple_dict(
                    plugin_info, color="yellow", indent=2
                )
                print()

        # Show available tasks
        elif args.available_tasks:
            # Get all available tasks and group them by plugin
            tasks = get_combined_plugin_tasks()
            grouped = defaultdict(list)
            for key in tasks.keys():
                group = key.split("/", 1)[0]
                grouped[group].append(key)

            # Print available tasks
            logger.padded_print("Available Tasks", "cyan")
            for plugin_name, task_list in grouped.items():
                logger.richprint(f"- {plugin_name}:", "green")
                for task_name in task_list:
                    logger.richprint(f"  - {task_name}", "yellow")

        # Show required plugin structure
        elif args.structure:
            logger.padded_print("Structure of 'gurk-plugin.yaml'", "cyan")
            print_typed_dict_types(Plugin)
            print()

            logger.padded_print(
                "Structure of 'project' section in 'pyproject.toml'", "cyan"
            )
            print_typed_dict_types(PluginMetadata)

        # Print system information
        elif args.system_info:
            # Get system info without internal fields
            system_info = get_system_info()
            del system_info["simulate_hardware"]

            # Print system info
            logger.padded_print("System information", "cyan")
            logger.pprint_simple_dict(
                system_info, color="yellow", capitalize=True
            )
