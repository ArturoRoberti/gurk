from argparse import ArgumentTypeError
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from gurk.lib.core import core
from gurk.lib.logger import ActiveLogger, Logger, allow_missing_logger
from gurk.lib.utils.configs import load_toml
from gurk.lib.utils.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    PluginSpecificationEnum,
    get_plugin_data,
    install_plugin,
    is_plugin_installed,
    load_raw_plugin_manifest,
)
from gurk.lib.utils.remotes import is_git_repo
from gurk.lib.utils.tasks import COMMON_RESOLVED_TASK_DICT_FIELDS


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
        def identity(x: str) -> str:
            return x

        if transform is None:
            transform = identity

        if check_function(transform(specification)):
            return ParsedSpecification(
                specification=specification,
                specification_type=specification_type,
                plugin=transform(specification),
                subtask=None,
                option="default",
            )
        elif possible_option and check_function(
            transform(possible_option_plugin)
        ):
            return ParsedSpecification(
                specification=specification,
                specification_type=specification_type,
                plugin=transform(possible_option_plugin),
                subtask=None,
                option=possible_option,
            )
        elif possible_subtask and check_function(
            transform(possible_subtask_plugin)
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

    # Git remote
    git_remote_specification = check_specification_type(
        PluginSpecificationEnum.GIT_REMOTE, is_git_repo
    )
    if git_remote_specification:
        return git_remote_specification

    # Installed plugin name
    def check_installed_plugin_name(plugin_name: str) -> bool:
        with allow_missing_logger():
            return is_plugin_installed(plugin_name, require_venv=True)

    installed_plugin_specification = check_specification_type(
        PluginSpecificationEnum.PLUGIN_NAME, check_installed_plugin_name
    )
    if installed_plugin_specification:
        return installed_plugin_specification

    # If none of the above checks succeeded, raise an error
    raise ArgumentTypeError(
        f"Invalid PluginSpecification '{specification}': Could not parse plugin specification. "
        "Please specify a valid plugin name, remote Git repository, or local directory, "
        "optionally followed by a task (using '/') or run option (using ':')."
    )


class RunNamespace(DefaultNamespace):
    # fmt: off
    specification: ParsedSpecification
    replace:       bool
    # fmt: on


def main(argv, prog, description):
    # Only parse 'run' specific args, keep the rest for later
    positional_ind = next(
        (i for i, arg in enumerate(argv) if not arg.startswith("-")), len(argv)
    )
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
        metavar="plugin[:<option> | /<task_name>]",
        help="plugin specification (local path, remote (optionally including version/commit/branch) or name) of the plugin to run, with optional run option or task name appended",
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Replace an existing plugin of a different version if it already exists",
    )
    args = parser.parse_args(run_argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        if args.specification.specification_type in (
            PluginSpecificationEnum.LOCAL_PATH,
            PluginSpecificationEnum.GIT_REMOTE,
        ):
            # (Re)install plugin if necessary
            if not install_plugin(
                args.specification.plugin, reinstall=args.replace
            ):
                logger.fatal(
                    f"Failed to install plugin from '{args.specification.plugin}'."
                )

            # Get plugin specification
            if (
                args.specification.specification_type
                == PluginSpecificationEnum.LOCAL_PATH
            ):
                try:
                    plugin_spec = load_toml(
                        Path(args.specification.plugin) / "pyproject.toml"
                    )["project"]["name"]
                except Exception as e:
                    logger.fatal(
                        f"Unexpected: Failed to load plugin name from local path '{args.specification.plugin}': {str(e)}"
                    )
            else:
                plugin_spec = args.specification.plugin
        else:
            # See if plugin is installed
            if not is_plugin_installed(
                args.specification.plugin, require_venv=True
            ):
                logger.fatal(
                    f"Plugin '{args.specification.plugin}' is not installed. Please install it first or change its specification."
                )

            # Get plugin specification
            plugin_spec = args.specification.plugin

        # CHECK: Plugin should now be installed
        if not is_plugin_installed(plugin_spec, require_venv=False):
            logger.fatal(
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
                logger.fatal(msg)
            ## Define mock option with the specific task enabled
            option = {task_name: {}}
        else:
            # Run the plugin default or specified option
            manifest_options = plugin_data["manifest"]["options"]
            option = manifest_options.get(args.specification.option)
            if not option:
                logger.fatal(
                    f"Plugin '{plugin_spec}' does not have a run option specified "
                    f"for '{args.specification.option}'. Available options "
                    f"are: {list(manifest_options.keys())}."
                )
            ## For any common fields, if they are missing in the raw
            ##  option, remove them (to be filled later) to use defaults
            raw_plugin_yaml = load_raw_plugin_manifest(plugin_spec)
            raw_option = raw_plugin_yaml["options"][args.specification.option]
            for (_, task), raw_task in zip(
                option.items(), raw_option.values()
            ):
                for field in COMMON_RESOLVED_TASK_DICT_FIELDS:
                    if field not in raw_task and field in task:
                        del task[field]

        # Generate task argparser base
        task_parser_base = GurkArgumentParser(
            prog=f"{prog} {args.specification.original}",
            description=f"Options to run {args.specification.original}",
            add_verbose_arg=False,
            add_non_interactive_arg=False,
            add_force_arg=True,
            add_task_args=False,
            allow_complex_types=False,
        )

        # Run task(s)
        core.main(
            option=option,
            cli_args=remaining,
            parser_base=task_parser_base,
        )

        # Final message
        logger.done(
            "All tasks completed - You may need to reboot for some changes to take effect"
        )
