from argparse import Namespace
from pathlib import Path

from gurk.lib.logger import allow_missing_logger
from gurk.lib.utils.plugins import GurkArgumentParser
from gurk.lib.utils.system_info import SystemInfo


class TaskNamespace(Namespace):
    system_info: SystemInfo
    config_file: Path | None
    force: bool


def parse_task_args(
    args: list[str],
) -> TaskNamespace:
    """
    Parse command-line arguments and return system info, config info, and remaining args.

    :param args: Arguments passed to the task, including task name at the start
    :type args: list[str]
    :return: Parsed system info, config file path, force flag and remaining arguments
    :rtype: tuple[SystemInfo, Path, bool, list[str]]
    """
    task_name, *remaining_args = args
    parser = GurkArgumentParser(
        add_verbose_arg=False,
        add_non_interactive_arg=False,
        add_force_arg=True,
        add_task_args=True,
    )
    with allow_missing_logger():
        parser.extend_task_arguments(task_name)

    args = parser.parse_args(remaining_args)
    return args
