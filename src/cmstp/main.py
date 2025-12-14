import click

from cmstp.cli import info, main_setup, pre_setup
from cmstp.cli.utils import (
    GROUP_CONTEXT_SETTINGS,
    SUBCOMMAND_CONTEXT_SETTINGS,
    get_prog,
)


@click.group(context_settings=GROUP_CONTEXT_SETTINGS)
def main():
    """cmstp - Package allowing a simple, automatic computer setup"""
    pass


@main.command(name="setup", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def setup_cmd(ctx):
    """Main setup utility - Set up your computer based on a provided configuration (or defaults)"""
    main_setup.main(ctx.args, prog=get_prog(ctx.info_name))


@main.command(name="info", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def info_cmd(ctx):
    """Print information about tasks, configuration files and the host system"""
    info.main(ctx.args, prog=get_prog(ctx.info_name))


@main.command(name="pre-setup", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def pre_setup_cmd(ctx):
    """(Recommended before setup) Run the user through some manual setups"""
    pre_setup.main(ctx.args, prog=get_prog(ctx.info_name))


if __name__ == "__main__":
    main()
