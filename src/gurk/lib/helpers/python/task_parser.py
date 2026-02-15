from gurk.lib.core.context import GurkContext
from gurk.lib.core.plugins import (
    GurkArgumentParser,
    TaskParserNamespace,
    get_resolved_plugin_manifest,
)
from gurk.lib.utils.common import typecheck


@typecheck
def _extend_task_arguments(parser: GurkArgumentParser, task_name: str) -> None:
    """
    Extend the parser with task-specific arguments defined in a plugin, if any.

    :param parser: Argument parser to extend with task-specific arguments
    :type parser: GurkArgumentParser
    :param task_name: Full name of a task in the form 'plugin_name/task_name'
    :type task_name: str
    :raises ValueError: If the plugin YAML could not be loaded or if the task arguments could not be found in the plugin manifest
    """
    plugin = task_name.split("/", 1)[0]
    plugin_manifest = get_resolved_plugin_manifest(plugin)
    if plugin_manifest is None:
        raise ValueError(f"Plugin '{plugin}' could not be loaded")

    try:
        task_args = plugin_manifest["tasks"][task_name]["args"]
        parser.extend_arguments(task_args)
    except KeyError as e:
        raise ValueError(
            f"Key 'tasks'/'{task_name}'/'args' not found "
            f"in plugin '{plugin}' YAML. Broken link: {e}"
        )


@typecheck
def parse_task_args(
    args: list[str],
) -> TaskParserNamespace:
    """
    Parse command-line arguments and return system info, config info, and remaining args.

    :param args: Arguments passed to the task, including task name at the start
    :type args: list[str]
    :return: Parsed system info, config file path, force flag and remaining arguments
    :rtype: TaskParserNamespace
    """
    task_name, *remaining_args = args
    parser = GurkArgumentParser[TaskParserNamespace](
        add_verbose_arg=False,
        add_non_interactive_arg=False,
        add_force_arg=True,
        add_task_args=True,
    )
    with GurkContext(logger=None, writable=False):
        _extend_task_arguments(parser, task_name)

    return parser.parse_args(remaining_args)
