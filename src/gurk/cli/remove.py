from gurk.lib.core.plugin_utils import GurkArgumentParser, remove_plugin
from gurk.lib.logger import ActiveLogger, Logger


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "plugins",
        type=str,
        nargs="+",
        help="Names of the plugins to remove",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        for plugin_name in args.plugins:
            remove_plugin(plugin_name)

        logger.done("Plugin removals completed.")
