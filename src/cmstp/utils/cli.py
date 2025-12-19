import getpass
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional, Tuple

from cmstp.core.logger import Logger
from cmstp.utils.common import generate_random_path, resolve_package_path
from cmstp.utils.git_repos import clone_git_files, is_git_repo
from cmstp.utils.interface import promt_bool
from cmstp.utils.logger import TaskTerminationType
from cmstp.utils.system_info import get_system_info
from cmstp.utils.yaml import load_yaml


def get_sudo_askpass() -> Path:
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
class MainSetupArgs:
    """
    Data class to hold main setup arguments.
    """

    # fmt: off
    config_file:         Path      = field(init=False, default=None)
    config_directory:    Path      = field(init=False, default=None)
    tasks:               List[str] = field(init=False, default_factory=list)
    enable_all:          bool      = field(init=False, default=False)
    enable_dependencies: bool      = field(init=False, default=False)
    disable_preparation: bool      = field(init=False, default=False)
    # fmt: on


@dataclass
class MainSetupProcessor:
    """
    Class to process main setup arguments and prepare the system.
    """

    # fmt: off
    logger: Logger        = field(repr=False)
    args:   MainSetupArgs = field(repr=False)
    argv:   List[str]     = field(repr=False)
    # fmt: on

    def prompt_pre_setup(self) -> None:
        pre_setup_done_file = Path.home() / ".cmstp" / "pre_setup.done"
        if not pre_setup_done_file.exists():
            print(
                "It seems that this is the first time you are running cmstp. "
                "It is recommended to run the pre-setup first to ensure all "
                "possible manual steps are taken care of."
            )
            if promt_bool("Would you like to run the pre-setup now?"):
                from cmstp.cli.pre_setup import main as pre_setup_main

                pre_setup_main([], prog="cmstp pre-setup")
                self.logger.info("Pre-setup completed")
            else:
                self.logger.warning("Skipping pre-setup")

            # Mark pre-setup as done
            pre_setup_done_file.parent.mkdir(parents=True, exist_ok=True)
            pre_setup_done_file.touch()

    def process_args(self) -> Tuple[MainSetupArgs, Optional[Path]]:
        """
        Docstring for process_args

        :return: Processed main setup arguments and optional cloned config directory path
        :rtype: Tuple[MainSetupArgs, Path | None]
        """
        main_setup_args = MainSetupArgs()
        cloned_config_dir = None

        # Tasks
        main_setup_args.tasks = self.args.tasks or []

        # Config directory
        if is_git_repo(str(self.args.config_directory)):
            # Git repo
            cloned_config_dir = generate_random_path(
                prefix="cmstp_config_dir_"
            )
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
        if self.args.tasks and not any(
            arg in self.argv for arg in ("-f", "--config-file")
        ):
            # If tasks are specified without a config file, ignore the config file
            self.args.config_file = None
        elif not self.args.config_file.exists():
            # If a config directory is specified, look for a config file there
            possible_config_file = (
                self.args.config_directory / self.args.config_file
            )
            if possible_config_file.exists():
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
        main_setup_args.config_file = resolved_config_file

        # Enable all
        main_setup_args.enable_all = (
            self.args.enable_all if self.args.enable_all else None
        )

        # Enable dependencies
        main_setup_args.enable_dependencies = (
            self.args.enable_dependencies
            if self.args.enable_dependencies
            else None
        )

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
        system_info = get_system_info()
        if system_info["name"] is None:
            self.logger.fatal(
                f"Unsupported OS type '{system_info['type']}'",
            )

        self.logger.debug(f"System information: {system_info}")

    def prepare(self) -> None:
        """
        Prepare the system for setup.
        """
        error_msg = None
        requirements_id = self.logger.add_task("install-requirements", total=2)

        result_update = subprocess.run(
            ["sudo", "apt-get", "update"],
            capture_output=True,
            text=True,
        )
        self.logger.update_task(requirements_id, "Updated apt packages")
        self.logger.debug(
            f"Preparation apt update output:\n{result_update.stdout}\n{result_update.stderr}"
        )

        result_upgrade = subprocess.run(
            ["sudo", "apt-get", "-y", "upgrade"],
            capture_output=True,
            text=True,
        )
        self.logger.update_task(requirements_id, "Upgraded apt packages")
        self.logger.debug(
            f"Preparation apt upgrade output:\n{result_upgrade.stdout}\n{result_upgrade.stderr}"
        )

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
            error_msg = "Failed to update/upgrade apt packages"
            if result_update.returncode != 0:
                error_msg += f"\nUpdate output:\n{result_update.stdout}\n{result_update.stderr}"
            if result_upgrade.returncode != 0:
                error_msg += f"\nUpgrade output:\n{result_upgrade.stdout}\n{result_upgrade.stderr}"
            self.logger.fatal(error_msg)

        self.logger.debug("System preparation completed successfully")

        return success
