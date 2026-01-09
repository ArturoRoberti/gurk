from gurk.plugin.utils import get_combined_plugin_registry
from gurk.utils.cli import CleanArgumentParser
from gurk.utils.common import PACKAGE_SRC_PATH


def main(argv, prog, description):
    parser = CleanArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "plugins",
        type=str,
        nargs="+",
        help="Names of the plugins to update. If empty, update all local plugins",
    )
    args = parser.parse_args(argv)

    if not args.plugins:
        # Get all local plugins to update if none specified
        combined_registry = get_combined_plugin_registry()
        args.plugins = combined_registry.keys()  # All plugin names

    # Update package plugins
    # TODO

    # Update local plugins
    for plugin_path in (PACKAGE_SRC_PATH / "plugins").iterdir():
        if not plugin_path.is_dir():
            continue
        # Check if plugin has a remote source
        gurk_plugin_yaml_path = plugin_path / "gurk-plugin.yaml"
        if not gurk_plugin_yaml_path.exists():
            continue
