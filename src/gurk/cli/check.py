from gurk.lib.core.context import GurkContext, Logger
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    check_local_plugin,
)


class CheckNamespace(DefaultNamespace):
    paths: list[str]


def main(argv, prog, description):
    parser = GurkArgumentParser[CheckNamespace](
        prog=prog, description=description
    )
    group = parser.add_required_group()
    group.add_argument(
        "paths",
        type=str,
        nargs="+",
        help="Local paths of custom plugins to check",
    )
    args = parser.parse_args(argv)

    # Execute without writing to plugins
    with GurkContext(
        logger=Logger(args.verbose, args.non_interactive), writable=False
    ) as ctx:
        for source in args.paths:
            if not check_local_plugin(source, True):
                ctx.logger.fatal(f"Plugin source '{source}' is invalid.")
            else:
                ctx.logger.info(f"Plugin source '{source}' is valid.")

        ctx.logger.done("Plugin checks complete.")
