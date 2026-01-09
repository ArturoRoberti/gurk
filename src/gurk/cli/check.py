from gurk.lib.core.plugin_utils import check_local_plugin
from gurk.lib.utils.cli import CleanArgumentParser


def main(argv, prog, description):
    parser = CleanArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "paths",
        type=str,
        nargs="+",
        help="Local paths of custom plugins to check",
    )
    args = parser.parse_args(argv)

    for source in args.paths:
        if not check_local_plugin(source):
            print(f"Plugin source '{source}' is invalid.")
        else:
            print(f"Plugin source '{source}' is valid.")
