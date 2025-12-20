import click

from cmstp.cli import commands, info, setup
from cmstp.cli.utils import (
    GROUP_CONTEXT_SETTINGS,
    SUBCOMMAND_CONTEXT_SETTINGS,
    VERSION,
    get_prog,
)


@click.group(context_settings=GROUP_CONTEXT_SETTINGS)
@click.version_option(version=VERSION, prog_name="cmstp")
def main():
    """cmstp - Package allowing a simple, automatic computer setup"""
    pass


@main.command(name="install", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def install_cmd(ctx: click.Context):
    """Run any of the cmstp installation tasks (see 'cmstp info --available-tasks')"""
    commands.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
        cmd=ctx.info_name,
    )


@main.command(name="configure", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def configure_cmd(ctx: click.Context):
    """Run any of the cmstp configuration tasks (see 'cmstp info --available-tasks')"""
    commands.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
        cmd=ctx.info_name,
    )


@main.command(name="uninstall", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def uninstall_cmd(ctx: click.Context):
    """Run any of the cmstp uninstallation tasks (see 'cmstp info --available-tasks')"""
    commands.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
        cmd=ctx.info_name,
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


@main.command(name="setup", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def setup_cmd(ctx: click.Context):
    """(Recommended before any main commands) Run the user through some manual setups"""
    setup.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


if __name__ == "__main__":
    main()
