from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import GurkArgumentParser, remove_plugin


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
            try:
                remove_plugin(plugin_name, purge=args.purge)
            except ModuleNotFoundError:
                logger.warning(
                    f"Plugin '{plugin_name}' is not (validly) installed. Ignoring..."
                )

        logger.done("Plugin removals completed.")
