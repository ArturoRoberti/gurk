import click

from gurk.cli import core, info, setup
from gurk.cli.utils import (
    CORE_COMMANDS,
    GROUP_CONTEXT_SETTINGS,
    SUBCOMMAND_CONTEXT_SETTINGS,
    VERSION,
    OrderedGroup,
    get_prog,
)


@click.group(cls=OrderedGroup, context_settings=GROUP_CONTEXT_SETTINGS)
@click.version_option(version=VERSION, prog_name="gurk")
def main():
    """gurk - Package manager easily allowing multiple simple and complex installations."""
    pass


def _add_core_cmd(cmd_name: str) -> None:
    """
    Dynamically add a core command to the main CLI group.

    :param cmd_name: Name of the command to add.
    :type cmd_name: str
    """
    help_text = f"Run any of the gurk '{cmd_name}' tasks (see 'gurk info --available-tasks')"

    @main.command(
        name=cmd_name,
        context_settings=SUBCOMMAND_CONTEXT_SETTINGS,
        help=help_text,
    )
    @click.pass_context
    def cmd(ctx: click.Context):
        core.main(
            argv=ctx.args,
            prog=get_prog(ctx.info_name),
            description=ctx.command.help,
            cmd=ctx.info_name,
        )

    cmd.__name__ = f"{cmd_name}_cmd"
    main.commands[cmd_name].category = "Core Commands"


# Add all 'core' commands dynamically
for cmd_name in CORE_COMMANDS:
    _add_core_cmd(cmd_name)


@main.command(name="setup", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def setup_cmd(ctx: click.Context):
    """(Recommended before any main commands) Run the user through some manual setups"""
    setup.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="info", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def info_cmd(ctx: click.Context):
    """Print information about tasks, configuration files and the host system"""
    info.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="pytest", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def pytest_cmd(ctx: click.Context):
    """Run pytest (able to import this package). Use as you would the normal 'pytest' command."""
    try:
        import pytest
    except ImportError:
        raise RuntimeError(
            "'pytest' is not installed. Please install this package with the "
            "'dev' extras to use this command via: 'pipx install -e .[dev]'"
        )
    raise SystemExit(pytest.main(ctx.args))


main.commands["pytest"].category = "Developer Commands"


if __name__ == "__main__":
    main()
