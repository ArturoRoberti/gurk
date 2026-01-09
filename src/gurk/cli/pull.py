from gurk.plugin.utils import import_plugin
from gurk.utils.cli import CleanArgumentParser

# TODO: Make so that any repo can be pulled, and then only the relevant paths defined in gurk-plugin.yaml are kept
#       That way, larger repositories can include gurk plugins, instead of requiring each plugin to be in its own repo


def main(argv, prog, description):
    parser = CleanArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "sources",
        type=str,
        nargs="+",
        help="Local paths or git URLs of the plugin sources to import",
    )
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="Update existing plugins if they already exist",
    )
    args = parser.parse_args(argv)

    for source in args.sources:
        if not import_plugin(source, args.update):
            print(f"Failed to import plugin from source '{source}'.")
            # TODO: Use logger (error)
            continue
