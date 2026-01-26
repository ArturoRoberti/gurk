import click

from gurk.cli import check, help, pull, remove, run, setup, template, upgrade
from gurk.cli.utils import (
    GROUP_CONTEXT_SETTINGS,
    SUBCOMMAND_CONTEXT_SETTINGS,
    VERSION,
    OrderedGroup,
    get_prog,
)


@click.group(cls=OrderedGroup, context_settings=GROUP_CONTEXT_SETTINGS)
@click.version_option(version=VERSION, prog_name="gurk")
def main():
    """gurk - Package manager making computer setup easy"""
    pass


#################################################################################################################
################################################# Core Commands #################################################
#################################################################################################################


@main.command(name="run", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def run_cmd(ctx: click.Context):
    """Run a gurk plugin or task"""
    run.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="upgrade", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def upgrade_cmd(ctx: click.Context):
    """Upgrade one or all gurk plugins to their newest state"""
    upgrade.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="pull", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def pull_cmd(ctx: click.Context):
    """Pull gurk plugins from git repositories"""
    pull.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="remove", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def remove_cmd(ctx: click.Context):
    """Remove one or more local gurk plugins"""
    remove.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="setup", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def setup_cmd(ctx: click.Context):
    """
    \b
    Run through some manual setups
      !!! Highly recommended before running any plugins/tasks !!!
    """
    setup.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="help", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def help_cmd(ctx: click.Context):
    """Show help about gurk. Use no arguments to see links to documentation."""
    help.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


for cmd in ["run", "upgrade", "pull", "setup", "remove", "help"]:
    main.commands[cmd].category = "Core Commands"


#################################################################################################################
########################################## Plugin Development Commands ##########################################
#################################################################################################################


@main.command(name="check", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def check_cmd(ctx: click.Context):
    """Check local gurk plugins for errors"""
    check.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="template", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def template_cmd(ctx: click.Context):
    """Copy the gurk plugin template to the current directory"""
    template.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


for cmd in ["check", "template"]:
    main.commands[cmd].category = "Plugin Development Commands"


#################################################################################################################
########################################### Gurk Development Commands ###########################################
#################################################################################################################


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


for cmd in ["pytest"]:
    main.commands[cmd].category = "Gurk Development Commands"


# Entry point
if __name__ == "__main__":
    main()
