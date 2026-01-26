import sys
from collections import OrderedDict
from importlib.metadata import version
from pathlib import Path
from textwrap import dedent

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
VERSION = version("gurk")


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
        # Build sections based on command categories
        sections = OrderedDict()
        commands = []
        for command in self.list_commands(ctx):
            # Get the command object
            cmd = self.get_command(ctx, command)
            if cmd is None:
                continue
            section = getattr(cmd, "category", "Other Commands")

            # Clean up help text
            help_text = dedent(cmd.help or "")

            # Add to the appropriate section
            sections.setdefault(section, []).append((command, help_text))

            # Keep track of all commands for width calculation
            commands.append(command)

        # Don't print anything if there are no commands
        if not commands:
            return

        # Compute a single indent to use across all sections
        # Indent counts from start of command name to start of help text
        indent_min = 10
        indent = max(indent_min, max(len(n) for n in commands))

        # Write sections
        for section_name, rows in sections.items():
            with formatter.section(section_name):
                padded_rows = [
                    (command.ljust(indent), help) for command, help in rows
                ]
                formatter.write_dl(padded_rows)

    def list_commands(self, ctx) -> list[str]:
        """
        (Overrides default) List commands in the order they were added.

        :param ctx: Click context
        :type ctx: click.Context
        :return: List of command names
        :rtype: list[str]
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
