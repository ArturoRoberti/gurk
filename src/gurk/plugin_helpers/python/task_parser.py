# Copyright 2026 Arturo Roberti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gurk.lib.context import GurkContext
from gurk.lib.core.plugins import (
    GurkArgumentParser,
    TaskParserNamespace,
    get_resolved_plugin_manifest,
)
from gurk.lib.utils import ListOrTuple, typecheck


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
    args: ListOrTuple[str],
) -> TaskParserNamespace:
    """
    Parse command-line arguments and return system info, config info, and remaining args.

    :param args: Arguments passed to the task, including task name at the start
    :type args: ListOrTuple[str]
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
