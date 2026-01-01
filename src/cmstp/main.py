import click

from cmstp.cli import core, info, setup
from cmstp.cli.utils import (
    CORE_COMMANDS,
    GROUP_CONTEXT_SETTINGS,
    SUBCOMMAND_CONTEXT_SETTINGS,
    VERSION,
    OrderedGroup,
    get_prog,
)


@click.group(cls=OrderedGroup, context_settings=GROUP_CONTEXT_SETTINGS)
@click.version_option(version=VERSION, prog_name="cmstp")
def main():
    """cmstp - Package allowing a simple, automatic computer setup"""
    pass


def _add_core_cmd(cmd_name: str) -> None:
    """
    Dynamically add a core command to the main CLI group.

    :param cmd_name: Name of the command to add.
    :type cmd_name: str
    """
    help_text = f"Run any of the cmstp '{cmd_name}' tasks (see 'cmstp info --available-tasks')"

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


if __name__ == "__main__":
    main()
