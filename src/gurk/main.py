import click

from gurk.cli import (
    _pytest,
    check,
    help,
    init,
    pull,
    remove,
    run,
    setup,
    template,
    upgrade,
)
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
    """Run a gurk plugin task or option"""
    run.main(
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


@main.command(name="upgrade", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def upgrade_cmd(ctx: click.Context):
    """Upgrade one or all installed gurk plugins to their newest version"""
    upgrade.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="init", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def init_cmd(ctx: click.Context):
    """Initialize gurk"""
    init.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="pull", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def pull_cmd(ctx: click.Context):
    """Install gurk plugins from git repositories or local paths"""
    pull.main(
        argv=ctx.args,
        prog=get_prog(ctx.info_name),
        description=ctx.command.help,
    )


@main.command(name="remove", context_settings=SUBCOMMAND_CONTEXT_SETTINGS)
@click.pass_context
def remove_cmd(ctx: click.Context):
    """Uninstall one or more gurk plugins (that are not officially supported)"""
    remove.main(
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


for cmd in ["run", "setup", "upgrade", "init", "pull", "remove", "help"]:
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
    """Create a gurk plugin template in the current directory"""
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
    """
    \b
    Run pytest (able to import this package). Use as you would the normal 'pytest' command.
      NOTE: Set the 'SUDO_ASKPASS' environment variable to include task-running tests
    """
    _pytest.main(argv=ctx.args)


for cmd in ["pytest"]:
    main.commands[cmd].category = "Gurk Development Commands"


# Entry point
if __name__ == "__main__":
    main()
