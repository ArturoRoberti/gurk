from gurk.lib.core.plugin_utils import remove_plugin
from gurk.lib.utils.cli import CleanArgumentParser


def main(argv, prog, description):
    parser = CleanArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "plugins",
        type=str,
        nargs="+",
        help="Names of the plugins to remove",
    )
    args = parser.parse_args(argv)

    for plugin_name in args.plugins:
        remove_plugin(plugin_name)
