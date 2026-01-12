from __future__ import annotations

import getpass
import json
import os
import re
import subprocess
import sys
from argparse import (
    SUPPRESS,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    ArgumentTypeError,
    Namespace,
    _ArgumentGroup,
)
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from gurk.lib.core.plugin_utils import (
    ResolvedGurkPlugin,
    load_resolved_plugin_yaml,
)
from gurk.lib.logger import Logger, TaskTerminationType, get_logger
from gurk.lib.utils.common import (
    ENABLED_CONFIG_FILE,
    SETUP_DONE_FILE,
    YES_ANSWERS,
    generate_random_path,
    resolve_package_path,
)
from gurk.lib.utils.interface import prompt_bool
from gurk.lib.utils.remotes import clone_git_files, is_git_repo
from gurk.lib.utils.system_info import SystemInfo, get_system_info
from gurk.lib.utils.yaml import load_yaml

if TYPE_CHECKING:
    from gurk.lib.utils.tasks import ResolvedArgsDefinitionCollection


def get_sudo_askpass() -> Path:
    """
    Create a temporary sudo askpass script that provides the user's sudo password.

    :return: Path to the temporary askpass script
    :rtype: Path
    """
    # Get logger
    logger = get_logger()

    # Reset sudo permissions
    subprocess.run(["sudo", "-k"])

    # Create temporary askpass file
    with NamedTemporaryFile(mode="w", delete=False) as askpass_file:
        attempts = 3
        while attempts > 0:
            response = logger.ask(
                f"\\[gurk] password for {getpass.getuser()}", True
            )
            test_response = subprocess.run(
                ["sudo", "-S", "-v"],
                input=response + "\n",
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if test_response.returncode == 0:
                break
            else:
                if attempts != 1:
                    print("Sorry, try again.")
                attempts -= 1
        else:
            print("gurk: 3 incorrect password attempts")
            sys.exit(1)

        askpass_file.write("#!/bin/sh\n" f"echo '{response}'\n")
        askpass_path = askpass_file.name

    os.chmod(askpass_path, 0o700)
    return askpass_path


def prompt_setup(answer: str | bool = None) -> None:
    """
    Prompt the user to run setup if it has never been run before.

    :param answer: Predefined answer for non-interactive mode (True/False for 'y'/'n').
    :type answer: bool | None
    """
    # Get logger
    logger = get_logger()

    if not SETUP_DONE_FILE.is_file():
        print(
            "It seems that this is the first time you are running gurk. "
            "It is recommended to run the setup first to ensure all "
            "possible manual steps are taken care of."
        )
        if logger.prompt_bool(
            "Would you like to run the setup now?",
            answer,
        ):
            from gurk.cli.setup import main as setup_main

            setup_main([], "", "")

        # Mark setup as done
        SETUP_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETUP_DONE_FILE.touch()


@dataclass
class CoreCliArgs:
    """
    Data class to hold main setup arguments.
    """

    # fmt: off
    gurk_cmd:            str       = field(init=False, default=None)
    config_file:         Path      = field(init=False, default=None)
    config_directory:    Path      = field(init=False, default=None)
    tasks:               list[str] = field(init=False, default_factory=list)
    enable_all:          bool      = field(init=False, default=False)
    enable_dependencies: bool      = field(init=False, default=False)
    disable_preparation: bool      = field(init=False, default=False)
    # fmt: on


@dataclass
class CoreCliProcessor:
    """
    Class to process main setup arguments and prepare the system.
    """

    # fmt: off
    logger:  Logger        = field(repr=False)
    args:    CoreCliArgs   = field(repr=False)
    argv:    list[str]     = field(repr=False)
    tasks:   list[str]     = field(repr=False)
    command: str           = field(repr=False)
    # fmt: on

    def process_args(self) -> tuple[CoreCliArgs, Path | None]:
        """
        Docstring for process_args

        :return: Processed main setup arguments and optional cloned config directory path
        :rtype: tuple[CoreCliArgs, Path | None]
        """
        main_setup_args = CoreCliArgs()
        cloned_config_dir = None

        # gurk command
        main_setup_args.gurk_cmd = self.command

        # Tasks
        main_setup_args.tasks = self.tasks or []

        # Config directory
        if is_git_repo(str(self.args.config_directory)):
            # Git repo
            cloned_config_dir = generate_random_path(prefix="gurk_config_dir_")
            cloned_path = clone_git_files(
                str(self.args.config_directory), dest_path=cloned_config_dir
            )
            if cloned_path is None:
                self.logger.fatal(
                    f"Failed to clone config directory "
                    f"git repo '{self.args.config_directory}'",
                )
            elif not cloned_path.is_dir():
                self.logger.fatal(
                    "Specified '--config-directory' is ",
                    f"actually not a directory: {cloned_path}",
                )
            else:
                main_setup_args.config_directory = cloned_path
        else:
            # Local path
            config_directory = resolve_package_path(self.args.config_directory)
            if config_directory is None:
                self.logger.fatal(
                    f"Config directory '{self.args.config_directory}' not found",
                )
            elif not config_directory.is_dir():
                self.logger.fatal(
                    f"Config directory '{self.args.config_directory}' is not a directory",
                )
            else:
                main_setup_args.config_directory = config_directory

        # Config file
        ## Check existence
        if self.tasks and self.args.config_file == ENABLED_CONFIG_FILE:
            # If tasks are specified without a config file, ignore the config file
            self.args.config_file = None
        elif not self.args.config_file.is_file():
            # If a config directory is specified, look for a config file there
            possible_config_file = (
                self.args.config_directory / self.args.config_file
            )
            if possible_config_file.is_file():
                self.args.config_file = possible_config_file
            elif is_git_repo(str(self.args.config_file)):
                # Git repo
                cloned_path = clone_git_files(
                    str(self.args.config_file),
                )
                if cloned_path is None:
                    self.logger.fatal(
                        f"Failed to clone config file git repo "
                        f"'{self.args.config_file}'",
                    )
                else:
                    self.args.config_file = cloned_path
            else:
                self.logger.fatal(
                    f"Config file '{self.args.config_file}' not found",
                )
        ## Special case: If no config file or tasks are specified, and
        ##   "--enable-all" is used, don't use package config file
        if (
            self.args.config_file == ENABLED_CONFIG_FILE
            and not self.tasks
            and self.args.enable_all
        ):
            self.logger.debug(
                f"Not using '{ENABLED_CONFIG_FILE.name}' as config file, as "
                "only '--enable-all' was specified"
            )
            self.args.config_file = None
        ## Validate
        resolved_config_file = resolve_package_path(self.args.config_file)
        if resolved_config_file is not None:
            config = load_yaml(resolved_config_file)
            if config is None:
                self.logger.warning(
                    "Config file does not exist or is not valid YAML - skipping it"
                )
                resolved_config_file = None
            elif not config:
                self.logger.warning("Config file is empty")
            elif not isinstance(config, dict):
                self.logger.fatal(
                    "Config file does not define a dict, "
                    f"but a {type(config).__name__}"
                )
        ## Safety in case of 'uninstall' command
        if (
            resolved_config_file == ENABLED_CONFIG_FILE
            and self.command == "uninstall"
        ):
            if not prompt_bool(
                "This will run EVERY uninstallation task available - are you sure?",
                "y" if self.args.yes else None,
            ):
                self.logger.done("Exiting...")
        main_setup_args.config_file = resolved_config_file

        # Enable all
        main_setup_args.enable_all = self.args.enable_all

        # Enable dependencies
        main_setup_args.enable_dependencies = self.args.enable_dependencies

        # Disable preparation
        main_setup_args.disable_preparation = self.args.disable_preparation

        self.logger.debug(
            f"Processed main setup args: {repr(main_setup_args)}"
        )

        return main_setup_args, cloned_config_dir

    def check_system_compatibility(self) -> None:
        """
        Check if the system is compatible for setup.
        """
        try:
            system_info = get_system_info()
        except Exception as e:
            self.logger.fatal(e)

        self.logger.debug(f"System information: {system_info}")

    def prepare(self) -> None:
        """
        Prepare the system for setup.
        """
        requirements_id = self.logger.add_task("gurk-preparation", total=2)
        log_file = self.logger.generate_logfile_path(requirements_id)

        # Update apt packages
        result_update = subprocess.run(
            ["sudo", "apt-get", "update"],
            capture_output=True,
            text=True,
        )
        self.logger.update_task(requirements_id, "Updated apt packages")
        with open(log_file, "a") as lf:
            lf.write(
                f"=== APT UPDATE OUTPUT ===\n{result_update.stdout}\n{result_update.stderr}\n"
            )

        # Upgrade apt packages
        result_upgrade = subprocess.run(
            ["sudo", "apt-get", "-y", "upgrade"],
            capture_output=True,
            text=True,
        )
        self.logger.update_task(requirements_id, "Upgraded apt packages")
        with open(log_file, "a") as lf:
            lf.write(
                f"=== APT UPGRADE OUTPUT ===\n{result_upgrade.stdout}\n{result_upgrade.stderr}\n"
            )

        # Determine and return success
        success = (
            result_update.returncode == 0 and result_upgrade.returncode == 0
        )
        self.logger.finish_task(
            requirements_id,
            success=TaskTerminationType.SUCCESS
            if success
            else TaskTerminationType.FAILURE,
        )
        if not success:
            self.logger.fatal("Failed to run preparation steps")

        self.logger.debug("System preparation completed successfully")
        return success


class CleanHelpFormatter(ArgumentDefaultsHelpFormatter):
    """
    Custom formatter that:
      - hides default=None and default=False for boolean flags
      - annotates mutually exclusive args automatically
      - respects max_help_position
    """

    def __init__(self, prog):
        super().__init__(prog, max_help_position=60)

    def _get_help_string(self, action):
        if action.default not in (None, SUPPRESS):
            # A default is specified and is not purposefully suppressed
            # NOTE: Inludes boolean flags ("store_true"/"store_false")
            default_suffix = f"(default: {action.default!s})"
            if not action.help:
                return default_suffix
            else:
                return action.help + " " + default_suffix
        else:
            # No default specified or default is purposefully suppressed
            return action.help or ""


class GurkArgumentParser(ArgumentParser):
    """
    Custom ArgumentParser that uses CleanHelpFormatter and adds common gurk CLI options.
    """

    def __init__(
        self,
        add_verbose_arg: bool = True,
        add_non_interactive_arg: bool = True,
        add_force_arg: bool = False,
        add_task_args: bool = False,
        allow_complex_types: bool = True,
        *args,
        **kwargs,
    ):
        # Some gurk internal variables
        self.required_group_title = "required arguments"
        self.add_non_interactive_arg = add_non_interactive_arg
        self.allow_complex_types = allow_complex_types

        # Use CleanHelpFormatter
        kwargs["formatter_class"] = lambda prog: CleanHelpFormatter(prog)

        # Call super init
        super().__init__(*args, **kwargs)

        # Add logger options
        if add_verbose_arg:
            self.add_argument(
                "-v",
                "--verbose",
                action="store_true",
                help="Enable verbose output",
            )
        if add_non_interactive_arg:
            self.add_argument(
                "--non-interactive",
                action="store_true",
                help="Run in non-interactive mode (disable prompts)",
            )
        if add_task_args:
            self._add_task_args()
        if add_force_arg:
            self.add_argument(
                "-f",
                "--force",
                action="store_true",
                help="Force execution of task(s) even if they don't need to run",
            )

    def _add_task_args(self) -> None:
        """
        Add common task arguments to the parser.

        :raises ArgumentTypeError: If argument validation fails
        """

        # Add system-info argument
        def json_dict(value: str) -> SystemInfo:
            """
            Validate that the input is a JSON object (dictionary).

            :param value: Input string
            :type value: str
            :return: Parsed JSON object
            :rtype: dict
            :raises ArgumentTypeError: If the input is not a valid JSON object
            """
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as e:
                raise ArgumentTypeError(f"Invalid JSON for --system-info: {e}")
            if not isinstance(parsed, dict):
                raise ArgumentTypeError(
                    "--system-info must be a JSON object (dictionary)"
                )
            return parsed

        self.add_argument(
            "--system-info",
            type=json_dict if self.allow_complex_types else str,
            required=True,
            help="JSON object with system information",
        )

        # Add config-file argument
        def existing_path(value: str) -> Path:
            """
            Validate that the input path exists.

            :param value: Input path string
            :type value: str
            :return: Path object
            :rtype: Path
            :raises ArgumentTypeError: If the path does not exist
            """
            path = Path(value)
            if not path.exists():
                raise ArgumentTypeError(f"Config file not found: {path}")
            return path

        self.add_argument(
            "--config-file",
            type=existing_path if self.allow_complex_types else str,
            default=None,
            help="Path to an existing config file",
        )

    def add_required_group(self) -> _ArgumentGroup:
        """
        Add a 'required arguments' group to the parser.

        :return: The created argument group
        :rtype: _ArgumentGroup
        """
        return self.add_argument_group(self.required_group_title)

    # TODO: Clean this up
    def extend_arguments(
        self, args_dict: ResolvedArgsDefinitionCollection
    ) -> None:
        """
        Extend the parser with arguments defined in a plugin.

        :param args_dict: Dictionary of argument definitions
        :type args_dict: ResolvedArgsDefinitionCollection
        """

        def make_wildcard_validator(patterns: list[str]):
            """
            Create:
            - an argparse type() validator supporting '*' wildcards
            - a matching metavar string
            """

            regexes = [
                re.compile("^" + re.escape(p).replace(r"\*", ".*") + "$")
                for p in patterns
            ]

            quoted = ", ".join(f"'{p}'" for p in patterns)
            metavar = "{" + ",".join(patterns) + "}"

            def validate(value: str) -> str:
                if any(rx.match(value) for rx in regexes):
                    return value
                raise ArgumentTypeError(
                    f"invalid choice: {value!r} (choose from {quoted})"
                )

            return validate, metavar

        # Collect mutually exclusive groups
        mutex_groups = defaultdict(list)
        for name, spec in args_dict.items():
            mutex = spec.get("mutex")
            if mutex:
                mutex_groups[mutex].append(name)

        argparse_mutex_groups = {
            name: self.add_mutually_exclusive_group() for name in mutex_groups
        }

        for name, spec in args_dict.items():
            help_text = spec.get("help")
            default = spec.get("default")
            nargs = spec.get("nargs")
            choices = spec.get("choices")

            kwargs = {}

            if help_text is not None:
                kwargs["help"] = help_text

            if choices is not None:
                validator, metavar = make_wildcard_validator(choices)
                kwargs["type"] = validator
                kwargs["metavar"] = metavar

            # --- Boolean flags ---
            if isinstance(default, bool):
                if nargs is not None:
                    raise ValueError(
                        f"Boolean flag '{name}' must not define nargs"
                    )

                kwargs["action"] = (
                    "store_true" if default is False else "store_false"
                )
                kwargs["default"] = default

            # --- Non-boolean arguments ---
            else:
                # if has_default:
                if default is not None:
                    # optional argument
                    kwargs["default"] = default
                elif nargs not in ("?", "*"):
                    # required argument
                    kwargs["required"] = True

                if nargs is not None:
                    kwargs["nargs"] = nargs

            # Choose correct target (parser or mutex group)
            mutex = spec.get("mutex")
            target = argparse_mutex_groups[mutex] if mutex else self

            target.add_argument(name, **kwargs)

    def extend_task_arguments(self, task_name: str) -> None:
        """
        Extend the parser with task-specific arguments defined in a plugin, if any.

        :param plugin: Plugin specification
        :type plugin: PluginSpec
        :raises ValueError: If the plugin YAML could not be loaded
        """
        plugin = task_name.split("/", 1)[0]
        plugin_yaml: ResolvedGurkPlugin = load_resolved_plugin_yaml(plugin)
        if not plugin_yaml:
            raise ValueError(f"Plugin '{plugin}' could not be loaded")

        try:
            task_args = plugin_yaml["define"]["tasks"][task_name]["args"]
            self.extend_arguments(task_args)
        except KeyError as e:
            self.error(
                f"Key 'define'/'tasks'/'{task_name}'/'args' not "
                f"found in plugin '{plugin}' YAML. Broken link: {e}"
            )

    def _reorder_actions(self):
        """
        Reorder actions to have required ones first.
        """
        # Reorder action groups to have 'required arguments' first
        required_group = None
        for g in self._action_groups:
            if g.title == self.required_group_title:
                required_group = g
                break
        if required_group:
            self._action_groups.remove(required_group)
            self._action_groups.insert(0, required_group)

    def print_help(self, file=None) -> None:
        # Reorder action groups to have 'required arguments' first
        self._reorder_actions()

        # Call the original print_help
        return super().print_help(file)

    def parse_args(
        self, args: Sequence[str] | None = None, namespace: None = None
    ) -> Namespace:
        # Reorder action groups to have 'required arguments' first
        self._reorder_actions()

        # Call the original parse_args
        args = super().parse_args(args, namespace)

        # Get non-interactive mode from env var if not specified
        if self.add_non_interactive_arg and not args.non_interactive:
            args.non_interactive = (
                os.getenv("GURK_NON_INTERACTIVE", "false").lower()
                in YES_ANSWERS
            )

        return args
