from gurk.lib.core.plugin_utils import GurkArgumentParser, check_local_plugin
from gurk.lib.logger import ActiveLogger, Logger


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
            if not check_local_plugin(source):
                logger.fatal(f"Plugin source '{source}' is invalid.")
            else:
                logger.info(f"Plugin source '{source}' is valid.")

        logger.done("Plugin checks complete.")
