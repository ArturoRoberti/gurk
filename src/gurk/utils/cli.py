import getpass
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional, Tuple

from gurk.core.logger import Logger
from gurk.utils.common import (
    ENABLED_CONFIG_FILE,
    generate_random_path,
    resolve_package_path,
)
from gurk.utils.git_repos import clone_git_files, is_git_repo
from gurk.utils.interface import prompt_bool
from gurk.utils.logger import TaskTerminationType
from gurk.utils.system_info import get_system_info
from gurk.utils.yaml import load_yaml


def get_sudo_askpass() -> Path:
    """
    Create a temporary sudo askpass script that provides the user's sudo password.

    :return: Path to the temporary askpass script
    :rtype: Path
    """
    # Reset sudo permissions
    subprocess.run(["sudo", "-k"])

    # Create temporary askpass file
    with NamedTemporaryFile(mode="w", delete=False) as askpass_file:
        attempts = 3
        while attempts > 0:
            response = getpass.getpass(
                "[sudo] password for {}: ".format(getpass.getuser())
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
            print("sudo: 3 incorrect password attempts")
            sys.exit(1)

        askpass_file.write("#!/bin/sh\n" f"echo '{response}'\n")
        askpass_path = askpass_file.name

    os.chmod(askpass_path, 0o700)
    return askpass_path


@dataclass
class CoreCliArgs:
    """
    Data class to hold main setup arguments.
    """

    # fmt: off
    gurk_cmd:           str       = field(init=False, default=None)
    config_file:         Path      = field(init=False, default=None)
    config_directory:    Path      = field(init=False, default=None)
    tasks:               List[str] = field(init=False, default_factory=list)
    enable_all:          bool      = field(init=False, default=False)
    enable_dependencies: bool      = field(init=False, default=False)
    disable_preparation: bool      = field(init=False, default=False)
    # fmt: on


SETUP_DONE_FILE = Path.home() / ".gurk" / "setup.done"


@dataclass
class CoreCliProcessor:
    """
    Class to process main setup arguments and prepare the system.
    """

    # fmt: off
    logger:  Logger        = field(repr=False)
    args:    CoreCliArgs   = field(repr=False)
    argv:    List[str]     = field(repr=False)
    tasks:   List[str]     = field(repr=False)
    command: str           = field(repr=False)
    # fmt: on

    def prompt_setup(self) -> None:
        """
        Prompt the user to run setup if it has never been run before.
        """
        if not SETUP_DONE_FILE.is_file():
            print(
                "It seems that this is the first time you are running gurk. "
                "It is recommended to run the setup first to ensure all "
                "possible manual steps are taken care of."
            )
            if prompt_bool(
                "Would you like to run the setup now?",
                "y" if self.args.yes else None,
            ):
                from gurk.cli.setup import main as setup_main

                setup_main([], "", "")
                self.logger.info("Setup completed")
            else:
                self.logger.warning("Skipping setup")

            # Mark setup as done
            SETUP_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
            SETUP_DONE_FILE.touch()

    def process_args(self) -> Tuple[CoreCliArgs, Optional[Path]]:
        """
        Docstring for process_args

        :return: Processed main setup arguments and optional cloned config directory path
        :rtype: Tuple[CoreCliArgs, Path | None]
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
