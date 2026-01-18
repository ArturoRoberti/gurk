from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import GurkArgumentParser, check_local_plugin


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "paths",
        type=str,
        nargs="+",
        help="Local paths of custom plugins to check",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        for source in args.paths:
            if not check_local_plugin(source, True):
                logger.fatal(f"Plugin source '{source}' is invalid.")
            else:
                logger.info(f"Plugin source '{source}' is valid.")

        logger.done("Plugin checks complete.")
