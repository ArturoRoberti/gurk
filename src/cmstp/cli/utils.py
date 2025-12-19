import sys
from pathlib import Path

import toml

GROUP_CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 200,
}
SUBCOMMAND_CONTEXT_SETTINGS = {
    "ignore_unknown_options": True,
    "allow_extra_args": True,
    "help_option_names": [],
}
VERSION = toml.load(f"{Path(__file__).parents[3]}/pyproject.toml")["project"][
    "version"
]


def get_prog(info_name: str) -> str:
    """
    Build a prog string for argparse subcommands.

    :param info_name: Name of the subcommand
    :type info_name: str
    :return: The program string for later usage in argparse
    :rtype: str
    """
    return f"{Path(sys.argv[0]).name} {info_name}"
