from gurk.lib.core.plugin_utils import GurkArgumentParser, pull_plugin
from gurk.lib.logger import ActiveLogger, Logger

# TODO: Make so that any repo can be pulled, and then only the relevant paths defined in gurk-plugin.yaml are kept
#       That way, larger repositories can include gurk plugins, instead of requiring each plugin to be in its own repo
# TODO: Create 'gurk clean' command for the above and to remove invalid plugins (and cache?). If any can be removed, prmpt user and ask for confirmation for those unless --non-interactive is set
#       Maybe unify with 'gurk remove' command?


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "sources",
        type=str,
        nargs="+",
        help="Git URLs of the plugin sources to import",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        for source in args.sources:
            if not pull_plugin(source):
                logger.error(
                    f"Failed to import plugin from source '{source}'."
                )
                continue

        logger.done("Plugin pull operations complete.")
