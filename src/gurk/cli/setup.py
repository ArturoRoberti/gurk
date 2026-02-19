import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

from gurk.lib.context import GurkContext, Logger, get_logger
from gurk.lib.core.plugins import DefaultNamespace, GurkArgumentParser
from gurk.lib.shared.printers import padded_print, richprint
from gurk.lib.shared.system_info import get_manufacturer
from gurk.lib.utils import SETUP_DONE_FILE


@dataclass
class SSHKeysManager:
    """
    Manage SSH keys for the user.
    """

    ssh_directory: Path = field(
        init=False, default=Path("~/.ssh").expanduser()
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

    def setup_key(self) -> None:
        # Get logger
        logger = get_logger()
        padded_print("New SSH Key", "cyan", 64)

        # Get key name
        padded_print("SSH Key Name", "yellow", 32, top=False, bottom=False)
        while True:
            key_name = logger.ask(
                "Enter a name for your SSH key (e.g. id_ed25519)"
            ).strip()
            if key_name:
                curr_ssh_key = self.ssh_directory / key_name
                ssh_key_pub_path = curr_ssh_key.with_suffix(".pub")
                if curr_ssh_key.is_file():
                    logger.warning(
                        f"Key '{key_name}' already exists. Please choose a different name.\n"
                    )
                    continue
                break
            else:
                logger.warning("Key name cannot be empty. Please try again.\n")

        # Get key password
        padded_print("SSH Key Password", "yellow", 32, top=False, bottom=False)
        while True:
            password = logger.ask(
                "Enter a password for the SSH key (can be empty)",
                password=True,
            )
            password_confirm = logger.ask(
                "Confirm the password", password=True
            )
            if password == password_confirm:
                break
            logger.warning("Passwords do not match. Try again.")

        # Create key
        os.makedirs(self.ssh_directory, exist_ok=True)
        subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                curr_ssh_key,
                "-N",
                password,
            ],
            capture_output=True,
        )
        subprocess.run(["eval", "$(ssh-agent -s)"], shell=True)
        subprocess.run(["ssh-add", curr_ssh_key])

        # Prompt the user to upload the public SSH key
        padded_print("SSH Key Upload", "yellow", 32, top=False, bottom=False)
        richprint(
            f"Please upload the public key ({ssh_key_pub_path}) to your account settings (GitHub, GitLab, etc.). Public key:"
        )
        with open(ssh_key_pub_path) as f:
            richprint(f.read().strip(), color="green")
        input("After uploading your key, press anything to continue...")

    def setup_keys(self) -> None:
        """
        Set up SSH keys by prompting the user for input.
        """
        # Get logger
        logger = get_logger()
        while True:
            self.setup_key()
            if not logger.prompt_bool(
                "Would you like to create another SSH key?"
            ):
                break
        logger.info("SSH key setup complete!")


@dataclass
class GitCredentialsManager:
    """
    Manage Git user credentials (name and email).
    """

    # fmt: off
    user_name:  str = field(default="")
    user_email: str = field(default="")
    # fmt: on

    def credentials_exist(self) -> bool:
        """
        Check if git user name and email are already set.

        :return: True if both user name and email are set, False otherwise
        :rtype: bool
        """
        # Get username
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

        # Get user email
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

        # Return whether both are set
        return bool(self.user_name and self.user_email)

    def setup_credentials(self) -> None:
        """Set up git user name and email."""
        # Get logger
        logger = get_logger()
        padded_print("Git User Info", "cyan", 64)

        # Prompt for username
        padded_print("Git User Name", "yellow", 32, top=False, bottom=False)
        while True:
            self.user_name = logger.ask("Enter your Git username").strip()
            if not self.user_name:
                logger.warning("Username cannot be empty. Please try again.")
                continue
            break

        # Prompt for email
        padded_print("Git User Email", "yellow", 32, top=False, bottom=False)
        while True:
            self.user_email = logger.ask("Enter your Git email").strip()
            if not self.user_email:
                logger.warning("Email cannot be empty. Please try again.")
                continue
            elif (
                "@" not in self.user_email
                or "." not in self.user_email.split("@")[-1]
            ):
                logger.warning("Invalid email format. Please try again.")
                continue
            break

        # Set credentials
        subprocess.run(
            ["git", "config", "--global", "user.name", self.user_name]
        )
        subprocess.run(
            ["git", "config", "--global", "user.email", self.user_email]
        )
        logger.info(
            f"Git user name and email set to '{self.user_name}' resp. '{self.user_email}'."
        )


def print_secure_boot_steps() -> None:
    """
    Print steps to disable Secure Boot in UEFI/BIOS.
    """
    # Get logger
    logger = get_logger()
    padded_print("Disable Secure Boot Steps", "cyan", 64)

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
    richprint(
        dedent(
            f"""\
            1. Reboot your computer. During the initial boot screen, repeatedly press one of the following keys to enter the UEFI/BIOS setup: {all_keys_str}
            2. Navigate to the 'Security' or 'Boot' tab using the arrow keys, locate the 'Secure Boot' option disable it.
            3. Save your changes and exit the UEFI/BIOS setup - Your computer will reboot with Secure Boot disabled.
        """
        )
    )


class SetupNamespace(DefaultNamespace):
    # fmt: off
    ssh_keys:            bool
    git_credentials:     bool
    disable_secure_boot: bool
    # fmt: on


def main(argv, prog, description):
    parser = GurkArgumentParser[SetupNamespace](
        prog=prog,
        description=description,
        add_verbose_arg=False,
        add_non_interactive_arg=False,
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

    # If none are enabled, enable all
    flags = vars(args)
    if not any(flags.values()):
        for flag in flags:
            flags[flag] = True

    # Execute without writing to plugins
    with GurkContext(
        logger=Logger(verbose=False, non_interactive=False, store_logs=False),
        writable=False,
    ) as ctx:
        # Set up SSH keys
        ssh_keys_manager = SSHKeysManager()
        ssh_keys_exist = ssh_keys_manager.keys_exist()
        if args.ssh_keys:
            if (
                not ssh_keys_exist
                and ctx.logger.prompt_bool(
                    "No SSH keys detected. Would you like to create SSH keys?"
                )
            ) or (
                ssh_keys_exist
                and ctx.logger.prompt_bool(
                    "Existing SSH keys detected. Would you still like to create new ones?"
                )
            ):
                ssh_keys_manager.setup_keys()
            ctx.logger.newline()

        # Set up Git Credentials
        git_credentials_manager = GitCredentialsManager()
        git_credentials_exist = git_credentials_manager.credentials_exist()
        if args.git_credentials:
            if (
                not git_credentials_exist
                and ctx.logger.prompt_bool(
                    "Git user name/email not set. Would you like to set them up?"
                )
            ) or (
                git_credentials_exist
                and ctx.logger.prompt_bool(
                    f"Git user name/email already set (to '{git_credentials_manager.user_name}' resp. '{git_credentials_manager.user_email}'). Would you like to update them?"
                )
            ):
                git_credentials_manager.setup_credentials()
            ctx.logger.newline()

        # Print Secure Boot disabling steps
        if args.disable_secure_boot and ctx.logger.prompt_bool(
            "Would you like to see the steps to disable Secure Boot in UEFI/BIOS?"
        ):
            print_secure_boot_steps()

        # Mark setup as done
        if not SETUP_DONE_FILE.is_file():
            SETUP_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
            SETUP_DONE_FILE.touch()
