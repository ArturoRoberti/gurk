from pathlib import Path

from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import GurkArgumentParser, remove_plugin
from gurk.lib.utils.remotes import is_git_repo


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "plugins",
        type=str,
        nargs="+",
        help="Names of the plugins to remove",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Purge plugin data completely instead of just removing local paths.",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        for plugin_name in args.plugins:
            # Only allow plugin names
            if is_git_repo(plugin_name) or Path(plugin_name).exists():
                logger.fatal(
                    f"Invalid plugin specification '{plugin_name}' given "
                    f"for removal. Only plugin names are allowed."
                )
                continue

            # Exclude gurk plugin, as it should not be removed
            if plugin_name == "gurk":
                logger.info(
                    "Skipping removal of core 'gurk' plugin, which cannot be removed."
                )
                continue

            # Attempt removal
            try:
                remove_plugin(plugin_name, purge=args.purge)
            except ModuleNotFoundError:
                logger.warning(
                    f"Plugin '{plugin_name}' is not (validly) installed. Ignoring..."
                )

        logger.done("Plugin removals completed.")
