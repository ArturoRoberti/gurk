import os
import subprocess
import sys
from pathlib import Path

GROUP_CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 200,
}  # optional: controls text wrapping
SUBCOMMAND_CONTEXT_SETTINGS = {
    "ignore_unknown_options": True,
    "allow_extra_args": True,
    "help_option_names": [],
}


def get_prog(info_name: str) -> str:
    """Build a prog string for argparse subcommands."""
    return f"{Path(sys.argv[0]).name} {info_name}"


def get_sudo_access() -> None:
    """Request sudo access from the user (unless help is asked)."""
    if not {"-h", "--help"} & set(sys.argv) and not os.geteuid() == 0:
        # Call the same script with sudo
        result = subprocess.call(["sudo", "-E", *sys.argv])
        sys.exit(result)
