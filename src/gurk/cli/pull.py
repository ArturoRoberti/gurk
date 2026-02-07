from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    install_plugin,
)
from gurk.lib.utils.remotes import is_git_installed


class PullNamespace(DefaultNamespace):
    sources: list[str]
    replace: bool


def main(argv, prog, description):
    parser = GurkArgumentParser[PullNamespace](
        prog=prog, description=description
    )
    parser.add_argument(
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

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        # Check that git is installed
        if not is_git_installed():
            logger.fatal(
                "Git is not installed or not available in PATH."
                "Please install it via 'sudo apt install git'"
            )

        # (Re)install specified plugins
        for source in args.sources:
            if not install_plugin(source, reinstall=args.replace):
                logger.error(f"Failed to pull plugin from source '{source}'.")
                continue

        logger.done("Plugin pulling complete.")
