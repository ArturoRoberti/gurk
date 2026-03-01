from gurk.lib.context import GurkContext, Logger
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    install_plugin,
)
from gurk.lib.shared.remotes import is_git_installed


class PullNamespace(DefaultNamespace):
    sources: list[str]
    replace: bool


def main(argv, prog, description):
    parser = GurkArgumentParser[PullNamespace](
        prog=prog, description=description
    )
    group = parser.add_required_group()
    group.add_argument(
        "sources",
        type=str,
        nargs="+",
        help="Local paths or GitQueries of the plugin to install from",
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Replace existing plugins if they already exist (in any form)",
    )
    args = parser.parse_args(argv)

    # Execute with writing to plugins
    with GurkContext(
        logger=Logger(
            verbose=args.verbose,
            non_interactive=args.non_interactive,
            description="Pulling plugins",
        ),
        writable=True,
    ) as ctx:
        # Check that git is installed
        if not is_git_installed():
            ctx.logger.fatal(
                "Git is not installed or not available in PATH."
                "Please install it via 'sudo apt install git'"
            )

        # (Re)install specified plugins
        for source in args.sources:
            install_plugin(source, reinstall=args.replace)

        ctx.logger.done("Plugin pulling complete.")
