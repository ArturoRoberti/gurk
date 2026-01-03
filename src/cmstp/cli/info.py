import sys
import traceback
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from typing import Any

from cmstp.core.logger import Logger, LoggerSeverity
from cmstp.utils.common import DEFAULT_CONFIG_FILE, ENABLED_CONFIG_FILE
from cmstp.utils.system_info import get_system_info
from cmstp.utils.yaml import load_yaml


def print_box_contents(filename: str) -> None:
    """
    Print the contents of a comment box from a file.

    :param filename: Path to the config file containing the comment box.
    :type filename: str
    """
    inside_box = False
    box_lines = []

    with open(filename, "r") as f:
        for line in f:
            stripped = line.rstrip(" \n")

            # Detect the top/bottom border of the box
            if stripped.startswith("#") and set(stripped) == {"#"}:
                if not inside_box:
                    inside_box = True  # Start of box
                else:
                    inside_box = False  # End of box
                    break  # Stop after the first box (remove this if multiple boxes exist)
                continue

            # Collect lines inside the box
            if inside_box:
                # Remove leading/trailing '#' and trailing spaces
                content = stripped.strip("#").rstrip()
                box_lines.append(content)

    Logger.richprint("\n".join(box_lines) + "\n")


def print_dict_aligned(
    data: Any, indent: int = 0, indent_step: int = 4, sort: bool = True
) -> None:
    """
    Print a dictionary or list with aligned formatting.

    :param data: The data structure (dict, list, or primitive) to print.
    :type data: Any
    :param indent: Current indentation level in spaces.
    :type indent: int
    :param indent_step: Number of spaces to indent per level.
    :type indent_step: int
    :param sort: Whether to sort the dictionary keys.
    :type sort: bool
    """

    def fmt_list(lst, lvl):
        if not lst:
            return "[]"
        if (
            all(isinstance(x, (str, int, float, bool)) for x in lst)
            and len(lst) <= 3
        ):
            return "[" + ", ".join(str(x) for x in lst) + "]"
        print("[")
        for x in lst:
            if isinstance(x, (dict, list)):
                print_dict_aligned(x, lvl + indent_step, indent_step, sort)
            else:
                print(" " * (lvl + indent_step) + str(x))
        print(" " * lvl + "]")
        return None

    if isinstance(data, dict):
        items = (
            sorted(data.items(), key=lambda x: str(x[0]))
            if sort
            else data.items()
        )
        maxlen = max((len(str(k)) for k in data), default=0)
        for k, v in items:
            key = str(k)
            if isinstance(v, dict):
                print(" " * indent + f"{key}:")
                print_dict_aligned(v, indent + indent_step, indent_step, sort)
            elif isinstance(v, list):
                inline = fmt_list(v, indent)
                if inline:
                    print(" " * indent + f"{key:<{maxlen}} : {inline}")
            else:
                print(" " * indent + f"{key:<{maxlen}} : {v}")
    elif isinstance(data, list):
        inline = fmt_list(data, indent)
        if inline:
            print(" " * indent + inline)
    else:
        print(" " * indent + str(data))


def main(argv, prog, description):
    parser = ArgumentParser(
        prog=prog,
        description=description,
        formatter_class=lambda prog: ArgumentDefaultsHelpFormatter(
            prog=prog,
            max_help_position=60,
        ),
    )
    parser.add_argument(
        "-s",
        "--system-info",
        action="store_true",
        help="Print system information",
    )
    parser.add_argument(
        "-t",
        "--tasks",
        type=str,
        nargs="+",
        default=None,
        help="Specify the tasks to print info about",
    )
    parser.add_argument(
        "-a",
        "--available-tasks",
        action="store_true",
        help="Print a list of all available tasks",
    )
    parser.add_argument(
        "-c",
        "--custom-config",
        action="store_true",
        help="Print info about the custom configuration file",
    )
    parser.add_argument(
        "-d",
        "--default-config",
        action="store_true",
        help="Print info about the default configuration file",
    )
    args = parser.parse_args(argv)

    # Ensure at least one option is provided
    if not (
        args.tasks
        or args.available_tasks
        or args.custom_config
        or args.default_config
        or args.system_info
    ):
        # Default: Print only system info
        args.system_info = True
    try:
        # Task info
        if args.tasks:
            # Get tasks info from default config
            default_config = load_yaml(DEFAULT_CONFIG_FILE)

            for task_name in args.tasks:
                if task_name not in default_config:
                    Logger.logrichprint(
                        LoggerSeverity.FATAL,
                        f"Task '{task_name}' not found in default configuration",
                    )
                    sys.exit(1)
                task_info = default_config[task_name]

                # Task properties/args
                Logger.richprint(
                    f"=== Task info for '{task_name}' ===", color="cyan"
                )
                print_dict_aligned(task_info, sort=False)

                # Task config file
                task_config_file = default_config[task_name]["config_file"]
                if task_config_file is not None:
                    Logger.richprint(
                        "\n--- Configuration file ---",
                        color="yellow",
                    )
                    content = Path(task_config_file).read_text()
                    Logger.richprint(content)
                print()  # Extra newline for better readability

        # Available tasks
        if args.available_tasks:
            # Get tasks info from default config
            default_config = load_yaml(DEFAULT_CONFIG_FILE)

            Logger.richprint("=== Available tasks ===", color="cyan")
            for task_name in default_config.keys():
                if task_name.startswith("_"):
                    continue  # Skip helpers
                print(task_name)
            print()  # Extra newline for better readability

        # Custom config info
        if args.custom_config:
            Logger.richprint(
                "=== Custom configuration file info ===", color="cyan"
            )
            print_box_contents(ENABLED_CONFIG_FILE)

        # Default config info
        if args.default_config:
            Logger.richprint(
                "=== Default configuration file info ===", color="cyan"
            )
            print_box_contents(DEFAULT_CONFIG_FILE)

        # System info
        if args.system_info:
            # Get system info without internal fields
            system_info = get_system_info()
            system_info.pop("simulate_hardware")

            Logger.richprint("=== System information ===", color="cyan")
            print_dict_aligned(system_info)

    except (KeyboardInterrupt, Exception) as e:
        traceback_str = traceback.format_exc()
        traceback_msg = (
            f"An Exception occured: {e.__class__.__name__} - {e}\n\n{traceback_str}"
            if str(e).strip()
            else ""
        )
        interrupt_msg = (
            "Process interrupted by user"
            if isinstance(e, KeyboardInterrupt)
            else traceback_msg
        )
        Logger.logrichprint(LoggerSeverity.FATAL, interrupt_msg, newline=True)
