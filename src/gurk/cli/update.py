from gurk.lib.core.plugin_utils import (
    GurkArgumentParser,
    get_combined_plugin_registry,
)
from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.remotes import is_git_repo


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "plugins",
        type=str,
        nargs="+",
        help="PluginSpec of the plugins to update. If empty, update all local plugins. If GitRefs are given, update any plugins using those remotes to those commits / branches.",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        if not args.plugins:
            # Get all local plugins to update if none specified
            combined_registry = get_combined_plugin_registry()
            args.plugins = combined_registry.keys()  # All plugin names

        for plugin in args.plugins:
            # Update plugin
            if is_git_repo(plugin):
                # TODO: If a git URL is given, clone/pull the plugin from that remote and remove existing version
                pass
            # TODO: If a plugin name or local path is given, update via git remote specified in gurk-plugin.yaml
            #       If a remote is given, update plugin to that remote and pull. These allow specific commits to be targeted.

            # Update plugin registry
            # TODO (use 'update_plugin_entry' from plugin_utils.py)
            pass
