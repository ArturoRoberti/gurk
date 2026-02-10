from argparse import Namespace
from collections import defaultdict
from copy import deepcopy

from gurk.lib.core.context import GurkContext, Logger, get_registries
from gurk.lib.core.plugins import (
    GURK_MANIFEST_FILENAME,
    GurkArgumentParser,
    PluginManifest,
    PluginMetadata,
    get_available_plugin_tasks,
    get_plugin_data,
    is_plugin_installed,
)
from gurk.lib.utils.common import PACKAGE_SRC_PATH
from gurk.lib.utils.configs import load_toml
from gurk.lib.utils.system_info import get_system_info
from gurk.lib.utils.typed_dict import print_typed_dict_types


class HelpNamespace(Namespace):
    # fmt: off
    plugins:           list[str] | None
    tasks:             list[str] | None
    available_plugins: bool
    available_tasks:   bool
    structure:         bool
    system_info:       bool
    # fmt: on


def main(argv, prog, description):
    parser = GurkArgumentParser[HelpNamespace](
        prog=prog,
        description=description,
        add_verbose_arg=False,
        add_non_interactive_arg=False,
    )
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
        "-s",
        "--structure",
        action="store_true",
        help="Show the required structure of a plugin",
    )
    group.add_argument(
        "--system-info",
        action="store_true",
        help="Print system information",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    with GurkContext(logger=Logger(False, False), writable=False) as ctx:
        # Print help about gurk itself
        if not any(vars(args).values()):
            # Load help from pyproject.toml
            gurk_toml = load_toml(
                PACKAGE_SRC_PATH.parents[1] / "pyproject.toml"
            )

            # Dictionary linking to gurk help
            gurk_help = {
                "Documentation": PACKAGE_SRC_PATH.parents[1] / "docs",
                "Homepage": gurk_toml["project"]["urls"]["Homepage"],
            }

            # Link to documentation
            ctx.logger.richprint(
                "For detailed help, visit the Gurk documentation:", "green"
            )
            ctx.logger.pprint_dict(gurk_help, color="yellow", indent=2)

        # Show help for specific plugins
        elif args.plugins:
            for plugin_name in args.plugins:
                # Check that the plugin is installed
                if not is_plugin_installed(plugin_name):
                    ctx.logger.error(
                        f"Plugin '{plugin_name}' is not installed."
                    )
                    continue

                # Re-get plugin name from metadata if available, in case another PluginSpecification was used
                plugin_data = get_plugin_data(plugin_name)
                plugin_name = plugin_data["metadata"]["name"]

                # Print general info
                ctx.logger.padded_print(
                    f"Plugin '{plugin_name}' General Info", "green"
                )
                general_info = deepcopy(plugin_data["metadata"])
                general_info["source"] = (
                    plugin_data["registration"]["remote"]
                    or plugin_data["registration"]["local"]
                )

                ctx.logger.pprint_dict(
                    general_info, color="yellow", capitalize=True
                )
                ctx.logger.newline()

                # Print tasks defined by the plugin
                plugin_manifest = plugin_data["manifest"]
                if plugin_manifest.get("tasks"):
                    ctx.logger.padded_print("Defined Tasks", "cyan")
                    for task_name, task_info in plugin_manifest[
                        "tasks"
                    ].items():
                        ctx.logger.richprint(f"- {task_name}:", "yellow")
                        ctx.logger.pprint_dict(task_info, color="cyan")
                        ctx.logger.newline()

                # Print imported plugins
                if plugin_manifest.get("imports"):
                    imports = {}
                    for imported_plugin in plugin_manifest["imports"]:
                        try:
                            plugin_data = get_plugin_data(imported_plugin)
                        except ModuleNotFoundError:
                            # Plugin is not installed
                            imports[imported_plugin] = "Not installed"
                        else:
                            # Plugin is installed - print source
                            imports[imported_plugin] = (
                                plugin_data["registration"]["remote"]
                                or plugin_data["registration"]["local"]
                            )

                    ctx.logger.padded_print("Imported Plugins", "cyan")
                    ctx.logger.pprint_dict(imports, color="yellow")
                    ctx.logger.newline()

                # Print 'options' section
                ctx.logger.padded_print("Run Options", "cyan")
                for option_name, option in plugin_manifest["options"].items():
                    key = plugin_name + (
                        " (default)"
                        if option_name == "default"
                        else f"={option_name}"
                    )
                    ctx.logger.richprint(f"- {key}: ", "yellow")
                    ctx.logger.pprint_dict(option, color="cyan")
                    ctx.logger.newline()

        # Show help for specific tasks
        elif args.tasks:
            # Get all available tasks
            tasks = get_available_plugin_tasks()
            ctx.logger.padded_print("Task Information", "cyan")

            for task_full_name in args.tasks:
                # Get task (if installed)
                task_info = tasks.get(task_full_name)
                if not task_info:
                    ctx.logger.error(
                        f"Task '{task_full_name}' is not installed."
                    )
                    continue

                # Print task info
                ctx.logger.richprint(f"Task '{task_full_name}':", "green")
                ctx.logger.pprint_dict(
                    task_info, color="yellow", capitalize=True, indent=2
                )
                ctx.logger.newline()

        # Show available plugins
        elif args.available_plugins:
            ctx.logger.padded_print("Available Plugins", "cyan")
            combined_registry = get_registries(
                home_registry=True, package_registry=True, combine=True
            )
            for plugin_name, plugin_info in combined_registry.items():
                ctx.logger.richprint(f"{plugin_name}:", "green")
                ctx.logger.pprint_dict(plugin_info, color="yellow", indent=2)
                ctx.logger.newline()

        # Show available tasks
        elif args.available_tasks:
            # Get all available tasks and group them by plugin
            tasks = get_available_plugin_tasks()
            grouped = defaultdict(list)
            for key in tasks.keys():
                group = key.split("/", 1)[0]
                grouped[group].append(key)

            # Print available tasks
            ctx.logger.padded_print("Available Tasks", "cyan")
            for plugin_name, task_list in grouped.items():
                ctx.logger.richprint(f"- {plugin_name}:", "green")
                for task_name in task_list:
                    ctx.logger.richprint(f"  - {task_name}", "yellow")

        # Show required plugin structure
        elif args.structure:
            ctx.logger.padded_print(
                f"Structure of '{GURK_MANIFEST_FILENAME}'", "cyan"
            )
            print_typed_dict_types(PluginManifest)
            ctx.logger.newline()

            ctx.logger.padded_print(
                "Structure of 'project' section in 'pyproject.toml'", "cyan"
            )
            print_typed_dict_types(PluginMetadata)

        # Print system information
        elif args.system_info:
            # Get system info without internal fields
            system_info = get_system_info()
            del system_info["simulate_hardware"]

            # Print system info
            ctx.logger.padded_print("System information", "cyan")
            ctx.logger.pprint_dict(
                system_info, color="yellow", capitalize=True
            )
