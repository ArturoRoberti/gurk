from pathlib import Path

from gurk.lib.context import GurkContext, Logger, get_registries
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    get_plugin_data,
    is_plugin_installed,
    upgrade_plugin,
)
from gurk.lib.shared.remotes import extract_url, is_git_installed


class UpgradeNamespace(DefaultNamespace):
    plugins: list[str]
    exclude: list[str] | None


def main(argv, prog, description):
    parser = GurkArgumentParser[UpgradeNamespace](
        prog=prog, description=description
    )
    group = parser.add_required_group()
    group.add_argument(
        "plugins",
        type=str,
        nargs="*",
        help="PluginSpecifications (name or remote) of the installed plugins to upgrade. If empty, upgrade all local plugins",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        type=str,
        nargs="+",
        help="PluginSpecifications (name or remote) to exclude from upgrade when upgrading all plugins",
    )
    args = parser.parse_args(argv)

    # Execute with writing to plugins
    with GurkContext(
        logger=Logger(args.verbose, args.non_interactive), writable=True
    ) as ctx:
        # Check that git is installed
        if not is_git_installed():
            ctx.logger.fatal(
                "Git is not installed or not available in PATH."
                "Please install it via 'sudo apt install git'"
            )

        # Parse plugin specifications to upgrade
        if args.plugins:
            plugins = args.plugins
            # Don't allow local paths
            for plugin in plugins:
                if Path(plugin).exists():
                    ctx.logger.error(
                        f"Invalid plugin specification '{plugin}' given for upgrade. "
                        f"Only plugin names or remotes are allowed. Skipping..."
                    )
                    plugins.remove(plugin)
        else:
            # Get all local plugins to upgrade if none specified
            combined_registry = get_registries(
                home_registry=True, package_registry=True, combine=True
            )
            plugins = combined_registry.keys()  # All plugin names

        # Check 'exclude' plugins if specified
        normalized_exclude = set()
        for exclude in args.exclude or []:
            # Don't allow local paths
            if Path(exclude).exists():
                ctx.logger.error(
                    f"Invalid plugin specification '{exclude}' given for exclusion. "
                    f"Only plugin names or remotes are allowed. Skipping..."
                )
                continue

            # Check that the plugin to exclude exists
            if not is_plugin_installed(exclude, require_venv=False):
                ctx.logger.warning(
                    f"Excluded plugin '{exclude}' is not validly installed. Ignoring..."
                )
                continue
            else:
                normalized_exclude.add(extract_url(exclude))

        for plugin in plugins:
            # Logging helper
            if args.plugins:
                logfunc = ctx.logger.info
            else:
                logfunc = ctx.logger.debug

            # Check if plugin is installed
            if not is_plugin_installed(
                extract_url(plugin), require_venv=False
            ):
                logfunc(
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
                logfunc(
                    f"Plugin '{plugin}' is local-only and has no remote. Skipping upgrade..."
                )
                continue

            # Exclude specified plugins
            if normalized_exclude & {
                plugin_name,
                str(plugin_local),
                extract_url(plugin_remote),
            }:
                logfunc(f"Excluding plugin '{plugin}' from upgrade.")
                continue

            # Upgrade plugin from remotes
            if not upgrade_plugin(plugin):
                ctx.logger.error(
                    f"Failed to upgrade plugin '{plugin}' from remote."
                )

        ctx.logger.done("Plugin upgrades complete.")
