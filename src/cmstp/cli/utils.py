import sys
from collections import OrderedDict
from importlib.metadata import version
from pathlib import Path
from typing import List

from click import Group

GROUP_CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 200,
}
SUBCOMMAND_CONTEXT_SETTINGS = {
    "ignore_unknown_options": True,
    "allow_extra_args": True,
    "help_option_names": [],
}
VERSION = version("cmstp")

CORE_COMMANDS = ["install", "uninstall", "configure"]


class OrderedGroup(Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commands = OrderedDict()

    def format_commands(self, ctx, formatter) -> None:
        """
        (Overrides default) Format commands in the help output, grouped by their 'category' attribute.

        :param ctx: Click context
        :type ctx: click.Context
        :param formatter: Click formatter
        :type formatter: click.HelpFormatter
        """
        sections = OrderedDict()
        for name in self.list_commands(ctx):
            # Get the command object
            cmd = self.get_command(ctx, name)
            if cmd is None:
                continue
            section = getattr(cmd, "category", "Other")

            # Clean up help text
            help_text = cmd.help or ""
            help_text = " ".join(
                line.strip() for line in help_text.splitlines() if line.strip()
            )

            sections.setdefault(section, []).append((name, help_text))

        for section_name, rows in sections.items():
            with formatter.section(section_name):
                formatter.write_dl(rows)

    def list_commands(self, ctx) -> List[str]:
        """
        (Overrides default) List commands in the order they were added.

        :param ctx: Click context
        :type ctx: click.Context
        :return: List of command names
        :rtype: List[str]
        """
        return list(self.commands.keys())


def get_prog(info_name: str) -> str:
    """
    Build a prog string for argparse subcommands.

    :param info_name: Name of the subcommand
    :type info_name: str
    :return: The program string for later usage in argparse
    :rtype: str
    """
    return f"{Path(sys.argv[0]).name} {info_name}"
