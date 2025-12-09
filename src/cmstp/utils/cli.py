import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from cmstp.core.logger import Logger
from cmstp.utils.common import generate_random_path, resolve_package_path
from cmstp.utils.git_repos import clone_git_files, is_git_repo
from cmstp.utils.system_info import get_system_info


@dataclass
class MainSetupArgs:
    # fmt: off
    tasks:               List[str] = field(init=False, default_factory=list)
    config_file:         Path      = field(init=False, default=None)
    config_directory:    Path      = field(init=False, default=None)
    disable_preparation: bool      = field(init=False, default=False)
    # fmt: on


@dataclass
class MainSetupProcessor:
    # fmt: off
    logger: Logger        = field(repr=False)
    args:   MainSetupArgs = field(repr=False)
    argv:   List[str]     = field(repr=False)
    # fmt: on

    def process_args(self) -> Tuple[MainSetupArgs, Optional[Path]]:
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
            self.args.config_directory = cloned_path
        else:
            # Local path
            self.args.config_directory = resolve_package_path(
                self.args.config_directory
            )
            if (
                self.args.config_directory is not None
                and self.args.config_directory.exists()
            ):
                if self.args.config_directory.is_file():
                    # If a file is specified, use its parent directory
                    self.args.config_directory = (
                        self.args.config_directory.parent
                    )
                # else: It's a directory, use as is
            else:
                self.logger.fatal(
                    f"Config directory not found: {self.args.config_directory}",
                )
        main_setup_args.config_directory = self.args.config_directory

        # Config file
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
            else:
                self.logger.fatal(
                    f"Config file not found: {self.args.config_file}",
                )
        main_setup_args.config_file = self.args.config_file

        # Disable preparation
        main_setup_args.disable_preparation = self.args.disable_preparation

        self.logger.debug(
            f"Processed main setup args: {repr(main_setup_args)}"
        )

        return main_setup_args, cloned_config_dir

    def check_system_compatibility(self) -> None:
        # Check system information
        system_info = get_system_info()
        if system_info["name"] is None:
            self.logger.fatal(
                f"Unsupported OS type '{system_info['type']}'",
            )

        self.logger.debug(f"System information: {system_info}")

    def prepare(self) -> None:
        error_msg = None
        requirements_id = self.logger.add_task("install-requirements", total=2)

        result_update = subprocess.run(
            ["sudo", "apt-get", "update"],
            capture_output=True,
            text=True,
        )
        self.logger.update_task(requirements_id, "Updated apt packages")

        result_upgrade = subprocess.run(
            ["sudo", "apt-get", "-y", "upgrade"],
            capture_output=True,
            text=True,
        )
        self.logger.update_task(requirements_id, "Upgraded apt packages")

        success = (
            result_update.returncode == 0 and result_upgrade.returncode == 0
        )
        self.logger.finish_task(requirements_id, success=success)

        if not success:
            error_msg = "Failed to update/upgrade apt packages"
            if result_update.returncode != 0:
                error_msg += f"\nUpdate output:\n{result_update.stdout}\n{result_update.stderr}"
            if result_upgrade.returncode != 0:
                error_msg += f"\nUpgrade output:\n{result_upgrade.stdout}\n{result_upgrade.stderr}"
            self.logger.fatal(error_msg)

        self.logger.debug("System preparation completed successfully")

        return success
