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

import os
import sys
from argparse import ArgumentTypeError
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import get_type_hints

from gurk.lib.context import (
    GurkContext,
    Logger,
    get_plugin_registration,
    is_plugin_registered,
)
from gurk.lib.core import runner
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    get_plugin_data,
    get_raw_plugin_manifest,
    install_plugin,
    is_plugin_installed,
)
from gurk.lib.shared.configs import load_toml
from gurk.lib.shared.plugins import PluginSpecificationEnum
from gurk.lib.shared.remotes import extract_url, is_git_installed, is_git_repo
from gurk.lib.shared.tasks import (
    ResolvedCustomTaskDict,
    ResolvedDefaultTaskDict,
)
from gurk.lib.utils import GURK_METADATA_FILENAME, identity


@dataclass(frozen=True)
class ParsedSpecification:
    """
    Dataclass to hold parsed PluginSpecification components. Only one of 'option' or 'task' will be set.
    """

    # fmt: off
    specification:      str
    specification_type: PluginSpecificationEnum
    plugin:             str | None
    subtask:            str | None
    option:             str | None
    # fmt: on


def parse_specification(specification: str) -> ParsedSpecification:
    """
    Parse a PluginSpecification string into its components.

    :param specification: The PluginSpecification string to parse
    :type specification: str
    :return: ParsedSpecification object containing the parsed components
    :rtype: ParsedSpecification
    :raises ArgumentTypeError: If the specification is invalid
    """
    possible_option_plugin, possible_option = (
        specification.rsplit(":", 1) + [None]
    )[:2]
    possible_subtask_plugin, possible_subtask = (
        specification.rsplit("/", 1) + [None]
    )[:2]

    def check_specification_type(
        specification_type: PluginSpecificationEnum,
        check_function: Callable[[str], bool],
        transform: Callable[[str], str] | None = None,
    ) -> ParsedSpecification | None:
        if transform is None:
            transform = identity
        # No subspecification
        if check_function(transform(specification)):
            return ParsedSpecification(
                specification=specification,
                specification_type=specification_type,
                plugin=transform(specification),
                subtask=None,
                option="default",
            )
        # Option specified
        elif (
            possible_option
            and extract_url(possible_option) == possible_option
            and check_function(transform(possible_option_plugin))
        ):
            return ParsedSpecification(
                specification=specification,
                specification_type=specification_type,
                plugin=transform(possible_option_plugin),
                subtask=None,
                option=possible_option,
            )
        # Subtask specified
        elif (
            possible_subtask
            and extract_url(possible_subtask) == possible_subtask
            and check_function(transform(possible_subtask_plugin))
        ):
            return ParsedSpecification(
                specification=specification,
                specification_type=specification_type,
                plugin=transform(possible_subtask_plugin),
                subtask=possible_subtask,
                option=None,
            )
        else:
            return None

    # Local path
    local_path_specification = check_specification_type(
        PluginSpecificationEnum.LOCAL_PATH,
        lambda path: Path(path).is_dir(),
        lambda path: str(Path(path).expanduser()),
    )
    if local_path_specification:
        return local_path_specification

    # Registered plugin name
    def check_registered_plugin_name(plugin_name: str) -> bool:
        with GurkContext(logger=None, writable=False):
            return is_plugin_registered(
                plugin_name,
                home_registry=True,
                package_registry=True,
                require_local=False,
            )

    registered_plugin_specification = check_specification_type(
        PluginSpecificationEnum.PLUGIN_NAME, check_registered_plugin_name
    )
    if registered_plugin_specification:
        return registered_plugin_specification

    # Git remote
    if is_git_installed():
        git_remote_specification = check_specification_type(
            PluginSpecificationEnum.GIT_REMOTE, is_git_repo
        )
        if git_remote_specification:
            return git_remote_specification
        git_msg = ""
    else:
        git_msg = " (NOTE: Git is not installed, so it cannot be used for plugin specifications) "

    # If none of the above checks succeeded, raise an error
    raise ArgumentTypeError(
        f"Invalid PluginSpecification '{specification}': Could not parse "
        f"plugin specification{git_msg}. Please specify an installed plugin "
        "name, remote Git repository, or local directory, optionally "
        "followed by a task (using '/') or run option (using ':')."
    )


class RunNamespace(DefaultNamespace):
    # fmt: off
    specification: ParsedSpecification
    replace:       bool
    askpass:       str | None
    # fmt: on


def main(argv, prog, description):
    # Only parse 'run' specific args, keep the rest for later
    positional_ind = 0
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("-"):
            i += 1
            if arg in ("-A", "--askpass"):
                i += 1  # Skip the argument value
            continue
        else:
            positional_ind = i
            break
    else:
        positional_ind = len(argv)
    run_argv, remaining = (
        argv[: positional_ind + 1],
        argv[positional_ind + 1 :],
    )

    # Build 'run' parser
    parser = GurkArgumentParser[RunNamespace](
        prog=prog, description=description
    )
    group = parser.add_required_group()
    group.add_argument(
        "specification",
        type=parse_specification,
        metavar="plugin[:<option> | /<task-subname>]",
        help="plugin specification (local path, remote (optionally including version/commit/branch) or name) of the plugin to run, with optional run option or task name appended",
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Replace an existing plugin of a different version if it already exists",
    )
    parser.add_argument(
        "-A",
        "--askpass",
        type=str,
        default=os.getenv("SUDO_ASKPASS"),
        help="Path to a script that echoes the sudo password, used for running tasks that require sudo. Can also be set with the 'SUDO_ASKPASS' environment variable.",
    )
    args = parser.parse_args(run_argv)

    # Execute with writing to plugins
    with GurkContext(
        logger=Logger(
            verbose=args.verbose,
            non_interactive=args.non_interactive,
            description="Processing plugin specification",
            vary_timestamp="pytest" in sys.modules,
        ),
        writable=True,
    ) as ctx:
        if args.specification.specification_type in (
            PluginSpecificationEnum.LOCAL_PATH,
            PluginSpecificationEnum.GIT_REMOTE,
        ):
            # (Re)install plugin if necessary
            if not install_plugin(
                args.specification.plugin, reinstall=args.replace
            ):
                ctx.logger.fatal(
                    f"Failed to install plugin from '{args.specification.plugin}'."
                )

            # Get plugin specification
            if (
                args.specification.specification_type
                == PluginSpecificationEnum.LOCAL_PATH
            ):
                try:
                    plugin_spec = load_toml(
                        Path(args.specification.plugin)
                        / GURK_METADATA_FILENAME
                    )["project"]["name"]
                except Exception as e:
                    ctx.logger.fatal(
                        f"Unexpected: Failed to load plugin name from local path '{args.specification.plugin}': {str(e)}"
                    )
            else:
                plugin_spec = args.specification.plugin
        else:
            # Install plugin if registered as remote-only
            if not is_plugin_installed(
                args.specification.plugin, require_venv=False
            ):
                registration = get_plugin_registration(
                    args.specification.plugin,
                    home_registry=True,
                    package_registry=True,
                    require_local=False,
                )
                remote = next(iter(registration.values()))["remote"]
                ctx.logger.debug(
                    f"Plugin '{args.specification.plugin}' is not installed. Pulling from remote '{remote}'..."
                )
                if not install_plugin(remote, reinstall=True):
                    ctx.logger.fatal(
                        f"Failed to pull plugin '{args.specification.plugin}' from '{remote}'."
                    )

            # Get plugin specification
            plugin_spec = args.specification.plugin

        # CHECK: Plugin should now be installed
        if not is_plugin_installed(plugin_spec, require_venv=False):
            ctx.logger.fatal(
                f"Unexpected: Plugin '{plugin_spec}' is still not installed."
            )

        # Get plugin data
        plugin_data = get_plugin_data(plugin_spec)

        # Create task option to run based on specification
        if args.specification.subtask:
            # Run a specific task
            task_name = f"{plugin_data['metadata']['name']}/{args.specification.subtask}"
            ## Check that the task exists in the plugin
            plugin_tasks = plugin_data["manifest"]["tasks"]
            if task_name not in plugin_tasks:
                msg = f"Plugin '{plugin_spec}' does not have a task named '{task_name}'."
                if not plugin_tasks:
                    msg += " This plugin defines no tasks."
                else:
                    msg += (
                        f" Available tasks are: {list(plugin_tasks.keys())}."
                    )
                ctx.logger.fatal(msg)
            ## Define mock option with the specific task enabled
            option = {task_name: {}}
        else:
            # Run the plugin default or specified option
            manifest_options = plugin_data["manifest"]["options"]
            option = manifest_options.get(args.specification.option)
            if not option:
                ctx.logger.fatal(
                    f"Plugin '{plugin_spec}' does not have a run option specified "
                    f"for '{args.specification.option}'. Available options "
                    f"are: {list(manifest_options.keys())}."
                )
            ## For any common fields, if they are missing in the raw
            ##  option, remove them (to be filled later) to use defaults
            common_fields = set(
                get_type_hints(ResolvedDefaultTaskDict).keys()
            ) & set(get_type_hints(ResolvedCustomTaskDict).keys())
            raw_plugin_yaml = get_raw_plugin_manifest(plugin_spec)
            raw_option = raw_plugin_yaml["options"][args.specification.option]
            for (_, task), raw_task in zip(
                option.items(), raw_option.values()
            ):
                for field in common_fields:
                    if field not in raw_task and field in task:
                        del task[field]

    # Execute without writing to plugins and with writing to logs
    with GurkContext(
        logger=Logger(
            verbose=args.verbose,
            non_interactive=args.non_interactive,
            description="Running specification",
            vary_timestamp="pytest" in sys.modules,
        ),
        writable=False,
    ) as ctx:
        if not (ctx.logger.can_prompt or ctx.logger.non_interactive):
            ctx.logger.fatal(
                "Cannot run tasks in interactive mode without a prompt-capable logger."
            )

        # Generate task argparser base
        task_parser_base = GurkArgumentParser(
            prog=f"{prog} {args.specification.specification}",
            description=f"Options to run {args.specification.specification}",
            add_verbose_arg=False,
            add_non_interactive_arg=False,
            add_force_arg=True,
            add_task_args=False,
            allow_complex_types=False,
        )

        # Run task(s)
        runner.main(
            option=option,
            cli_args=remaining,
            parser_base=task_parser_base,
            askpass=args.askpass,
        )

        # Final message
        ctx.logger.done(
            "All tasks completed - You may need to reboot for some changes to take effect"
        )
