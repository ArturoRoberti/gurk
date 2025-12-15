import getpass
import os
import subprocess
import traceback
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich import print as richprint

from cmstp.core.logger import Logger, LoggerSeverity
from cmstp.utils.system_info import get_manufacturer


def promt_bool(message: str) -> bool:
    """
    Prompt the user for a yes/no response.

    :param message: The prompt message.
    :type message: str
    :return: True if the user responds with 'y', False for 'n'.
    :rtype: bool
    """
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ["y", "n"]:
            return response == "y"
        else:
            richprint("Invalid input. Please enter 'y' or 'n'")


@dataclass
class SSHKeysManager:
    """
    Manage SSH keys for the user.
    """

    # fmt: off
    ssh_directory: Path           = field(init=False, default=Path("~/.ssh").expanduser())
    curr_ssh_key:  Optional[Path] = field(init=False, repr=False, default=None)
    # fmt: on

    @property
    def ssh_key_pub_path(self) -> Path:
        return (
            self.curr_ssh_key.with_suffix(".pub")
            if self.curr_ssh_key
            else None
        )

    def keys_exist(self) -> bool:
        """
        Check if any SSH keys are already added to the ssh-agent.

        :return: True if keys exist, False otherwise.
        :rtype: bool
        """
        try:
            output = (
                subprocess.check_output(
                    ["ssh-add", "-l"], stderr=subprocess.DEVNULL
                )
                .decode()
                .strip()
            )
            if "The agent has no identities" in output or not output:
                return False
            return True
        except subprocess.CalledProcessError:
            # ssh-agent may not be running
            return False

    def prompt_name(self) -> None:
        """
        Prompt the user for an SSH key name.
        """
        Logger.richprint("=== SSH Key Name ===", "cyan")
        while True:
            key_name = input(
                "Enter a name for your SSH key (e.g. id_ed25519): "
            ).strip()
            if key_name:
                self.curr_ssh_key = self.ssh_directory / key_name
                if self.curr_ssh_key.exists():
                    print(
                        f"Key '{key_name}' already exists. Please choose a different name.\n"
                    )
                    continue
                return
            else:
                print("Key name cannot be empty. Please try again.\n")

    def create(self) -> None:
        """
        Create a new SSH key pair and add it to the ssh-agent.
        """
        Logger.richprint("\n=== SSH Key Password ===", "cyan")
        while True:
            password = getpass.getpass(
                "Enter a password for the SSH key (can be empty): "
            )
            password_confirm = getpass.getpass("Confirm the password: ")
            if password == password_confirm:
                break
            print("Passwords do not match. Try again.\n")

        os.makedirs(self.ssh_directory, exist_ok=True)

        # Run ssh-keygen
        subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                self.curr_ssh_key,
                "-N",
                password,
            ],
            capture_output=True,
        )

        # Add key to ssh-agent
        subprocess.run(["eval", "$(ssh-agent -s)"], shell=True)
        subprocess.run(["ssh-add", self.curr_ssh_key])

        print(f"SSH key successfully created at {self.curr_ssh_key}")

    def prompt_upload(self) -> None:
        """
        Prompt the user to upload the public SSH key.
        """
        Logger.richprint("\n=== SSH Key Upload ===", "cyan")
        print(
            f"Please upload the public key ({self.ssh_key_pub_path}) in your account settings (GitHub, GitLab, etc.). Public key (between dashes):"
        )
        print("-" * 100)
        with open(self.ssh_key_pub_path) as f:
            print(f.read().strip())
        print("-" * 100)
        input("After uploading your key, press anything to continue...")

    def setup_keys(self) -> None:
        """
        Set up SSH keys by prompting the user for input.
        """
        while True:
            self.prompt_name()
            self.create()
            self.prompt_upload()
            Logger.richprint("\n=== New SSH Key ===", "cyan")
            if not promt_bool("Would you like to create another SSH key?"):
                break
            print()  # Newline for better readability
        Logger.richprint("SSH key setup complete!\n", "green")


@dataclass
class GitCredentialsManager:
    """
    Manage Git user credentials (name and email).
    """

    # fmt: off
    user_name:  str    = field(default="")
    user_email: str    = field(default="")
    # fmt: on

    def credentials_exist(self) -> bool:
        """
        Check if git user name and email are already set.

        :return: True if both user name and email are set, False otherwise
        :rtype: bool
        """
        self.get_credentials()
        return bool(self.user_name and self.user_email)

    def get_credentials(self) -> None:
        """Retrieve existing git user name and email if set."""
        try:
            self.user_name = (
                subprocess.check_output(
                    ["git", "config", "--global", "user.name"]
                )
                .decode()
                .strip()
            )
        except subprocess.CalledProcessError:
            self.user_name = ""

        try:
            self.user_email = (
                subprocess.check_output(
                    ["git", "config", "--global", "user.email"]
                )
                .decode()
                .strip()
            )
        except subprocess.CalledProcessError:
            self.user_email = ""

    def prompt_credentials(self) -> None:
        """
        Prompt the user for git user name and email.
        """
        Logger.richprint("=== Git User Info ===", "cyan")
        while True:
            self.user_name = input("Enter your Git username: ").strip()
            self.user_email = input("Enter your Git email: ").strip()
            if self.user_name and self.user_email:
                return
            print("Both username and email are required. Please try again.\n")

    def setup_credentials(self) -> None:
        """Set up git user name and email."""
        self.prompt_credentials()
        subprocess.run(
            ["git", "config", "--global", "user.name", self.user_name]
        )
        subprocess.run(
            ["git", "config", "--global", "user.email", self.user_email]
        )
        Logger.richprint(
            f"Git user name and email set to '{self.user_name}' resp. '{self.user_email}'\n",
            "green",
        )


def print_secure_boot_steps() -> None:
    """
    Print steps to disable Secure Boot in UEFI/BIOS.
    """
    Logger.richprint("=== Disable Secure Boot Steps ===", "cyan")

    # Table of common manufacturers → probable keys
    key_table = {
        "acer": ["F2", "Del", "F12"],
        "asus": ["F2", "Del"],
        "dell": ["F2", "F12"],
        "hp": ["Esc", "F10", "F2"],
        "lenovo": ["F1", "F2", "Novo button"],
        "msi": ["Del", "F11"],
        "gigabyte": ["Del"],
        "asrock": ["Del", "F2"],
        "toshiba": ["F2", "Esc"],
        "samsung": ["F2"],
        "sony": ["F2", "Assist button"],
        "microsoft": ["Volume Up"],
        "system76": ["F2", "Del"],
        "purism": ["Del", "Esc"],
    }

    # Find best match
    manufacturer = get_manufacturer()
    matches = [
        (name, keys)
        for name, keys in key_table.items()
        if name in manufacturer
    ]
    if not matches:
        all_keys_str = "Esc, Del, F1, F2, F10, F12"
    else:
        all_keys_str = ", ".join([key for _, keys in matches for key in keys])

    # Print steps
    print(
        f"1. Reboot your computer. During the initial boot screen, repeatedly press one of the following keys to enter the UEFI/BIOS setup: {all_keys_str}\n"
        "2. Navigate to the 'Security' or 'Boot' tab using the arrow keys, locate the 'Secure Boot' option disable it.\n"
        "3. Save your changes and exit the UEFI/BIOS setup - Your computer will reboot with Secure Boot disabled."
    )


def main(argv, prog):
    parser = ArgumentParser(
        prog=prog,
        description="Prepare some manual setups",
        formatter_class=lambda prog: ArgumentDefaultsHelpFormatter(
            prog=prog,
            max_help_position=30,
        ),
    )
    # Flags to short-circuit specific pre-setup tasks
    parser.add_argument(
        "-s",
        "--ssh-keys",
        action="store_true",
        help="Set up SSH keys without prompt",
    )
    parser.add_argument(
        "-g",
        "--git-credentials",
        action="store_true",
        help="Set up Git Credentials (username, email) without prompt",
    )
    parser.add_argument(
        "-d",
        "--disable-secure-boot",
        action="store_true",
        help="Print steps to disable Secure Boot in UEFI/BIOS",
    )
    args = parser.parse_args(argv)

    try:
        # Set up SSH keys
        ssh_keys_manager = SSHKeysManager()
        ssh_keys_exist = ssh_keys_manager.keys_exist()
        if (
            args.ssh_keys
            or (
                not ssh_keys_exist
                and promt_bool(
                    "No SSH keys detected. Would you like to create SSH keys?"
                )
            )
            or (
                ssh_keys_exist
                and promt_bool(
                    "Existing SSH keys detected. Would you still like to create new ones?"
                )
            )
        ):
            ssh_keys_manager.setup_keys()
        else:
            Logger.richprint("Skipping SSH key setup\n", "yellow")

        # Set up Git Credentials
        git_credentials_manager = GitCredentialsManager()
        git_credentials_exist = git_credentials_manager.credentials_exist()
        if (
            args.git_credentials
            or (
                not git_credentials_exist
                and promt_bool(
                    "Git user name/email not set. Would you like to set them up?"
                )
            )
            or (
                git_credentials_exist
                and promt_bool(
                    f"Git user name/email already set (to {git_credentials_manager.user_name} resp. {git_credentials_manager.user_email}). Would you like to update them?"
                )
            )
        ):
            git_credentials_manager.setup_credentials()
        else:
            Logger.richprint("Skipping Git credentials setup\n", "yellow")

        # Print Secure Boot disabling steps
        if args.disable_secure_boot or promt_bool(
            "Would you like to see the steps to disable Secure Boot in UEFI/BIOS?"
        ):
            print_secure_boot_steps()
        else:
            Logger.richprint("Skipping Secure Boot disabling steps", "yellow")

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
