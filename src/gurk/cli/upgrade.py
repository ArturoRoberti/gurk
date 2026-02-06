from pathlib import Path

from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    get_combined_plugin_registry,
    get_plugin_data,
    get_plugin_version,
    install_plugin,
    is_plugin_installed,
)
from gurk.lib.utils.remotes import edit_url, extract_url, get_latest_version


class UpgradeNamespace(DefaultNamespace):
    plugins: list[str]
    exclude: list[str] | None


def main(argv, prog, description):
    parser = GurkArgumentParser[UpgradeNamespace](
        prog=prog, description=description
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "plugins",
        type=str,
        nargs="*",
        help="PluginSpecifications (name or remote) of the installed plugins to upgrade. If empty, upgrade all local plugins",
    )
    group.add_argument(
        "-e",
        "--exclude",
        type=str,
        nargs="+",
        help="PluginSpecifications (name or remote) to exclude from upgrade when upgrading all plugins",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        if args.plugins:
            plugins = args.plugins

            # Don't allow local paths
            for plugin in plugins:
                if Path(plugin).exists():
                    logger.error(
                        f"Invalid plugin specification '{plugin}' given for upgrade. "
                        f"Only plugin names or remotes are allowed. Skipping..."
                    )
                    plugins.remove(plugin)
        else:
            # Get all local plugins to upgrade if none specified
            combined_registry = get_combined_plugin_registry()
            plugins = combined_registry.keys()  # All plugin names

        # Check 'exclude' plugins if specified
        normalized_exclude = set()
        for exclude in args.exclude or []:
            # Don't allow local paths
            if Path(exclude).exists():
                logger.error(
                    f"Invalid plugin specification '{exclude}' given for exclusion. "
                    f"Only plugin names or remotes are allowed. Skipping..."
                )
                continue

            # Check that the plugin to exclude exists
            if not is_plugin_installed(exclude, require_venv=False):
                logger.warning(
                    f"Excluded plugin '{exclude}' is not validly installed. Ignoring..."
                )
                continue
            else:
                normalized_exclude.add(extract_url(exclude))

        for plugin in plugins:
            # Logging helper
            if args.plugins and plugin in args.plugins:
                wlogfunc = logger.warning
                ilogfunc = logger.info
            else:
                wlogfunc = logger.debug
                ilogfunc = logger.debug

            # Check if plugin is installed
            if not is_plugin_installed(plugin, require_venv=False):
                wlogfunc(
                    f"Plugin '{plugin}' is not validly installed. Skipping upgrade..."
                )
                continue

            # Get plugin data
            plugin_data = get_plugin_data(plugin)
            plugin_name = plugin_data["metadata"]["name"]
            plugin_local = plugin_data["registration"]["local"]
            plugin_remote = plugin_data["registration"]["remote"]

            # Skip local-only plugins
            if not plugin_remote:
                ilogfunc(
                    f"Plugin '{plugin}' is local-only and has no remote. Skipping upgrade..."
                )
                continue

            # Exclude specified plugins
            if normalized_exclude & {
                plugin_name,
                plugin_local,
                extract_url(plugin_remote),
            }:
                ilogfunc(f"Excluding plugin '{plugin}' from upgrade.")
                continue

            # See if the current version is already the latest
            latest_version = get_latest_version(plugin_remote)
            if latest_version == get_plugin_version(plugin):
                ilogfunc(
                    f"Plugin '{plugin}' is already at the latest version. Skipping upgrade..."
                )
                continue

            # Upgrade plugin from remotes
            new_remote = edit_url(
                plugin_remote, version=latest_version, commit=None
            )
            if not install_plugin(new_remote, reinstall=True):
                logger.error(
                    f"Failed to upgrade plugin from remote '{new_remote}'."
                )

    logger.done("Plugin upgrades complete.")
