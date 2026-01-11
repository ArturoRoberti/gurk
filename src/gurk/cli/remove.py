from gurk.lib.core.plugin_utils import remove_plugin
from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.cli import GurkArgumentParser


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
    logger = Logger(args.verbose)
    with ActiveLogger(logger):
        for plugin_name in args.plugins:
            remove_plugin(plugin_name)
