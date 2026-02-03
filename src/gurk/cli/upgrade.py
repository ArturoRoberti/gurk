from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import (
    GurkArgumentParser,
    check_local_plugin,
    get_combined_plugin_registry,
    get_local_plugin_version,
    get_plugin_data,
    installed_plugin_path,
    pull_plugin,
    remove_plugin,
)
from gurk.lib.utils.remotes import extract_url, get_latest_version


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-p",
        "--plugins",
        type=str,
        nargs="+",
        help="PluginSpecs (name, local path or remote) of the plugins to upgrade. If empty, upgrade all local plugins.",
    )
    group.add_argument(
        "-e",
        "--exclude",
        type=str,
        nargs="+",
        help="PluginSpecs (name, local path or remote) to exclude from upgrade when upgrading all plugins.",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        if args.plugins:
            plugins = args.plugins
        else:
            # Get all local plugins to upgrade if none specified
            combined_registry = get_combined_plugin_registry()
            plugins = combined_registry.keys()  # All plugin names

        # Check that plugins to exclude exist
        normalized_exclude = set()
        for exclude in args.exclude or []:
            try:
                get_plugin_data(exclude)
            except ModuleNotFoundError:
                plugin_local = installed_plugin_path(exclude)
                part = "invalidly" if plugin_local else "not"
                logger.warning(
                    f"Excluded plugin '{exclude}' is {part} installed. Ignoring..."
                )
            else:
                normalized_exclude.add(extract_url(exclude))

        # Get remotes of specified plugins
        plugin_remotes = set()
        for plugin in plugins:
            # Logging helper
            if args.plugins and plugin in args.plugins:
                wlogfunc = logger.warning
                ilogfunc = logger.info
            else:
                wlogfunc = logger.debug
                ilogfunc = logger.debug

            # Get plugin data
            try:
                plugin_data = get_plugin_data(plugin)
            except ModuleNotFoundError:
                plugin_local = installed_plugin_path(plugin)
                if plugin_local:
                    # Plugin is installed, but invalid
                    check_local_plugin(plugin_local, True)
                    wlogfunc(
                        f"Plugin '{plugin}' is installed but invalid. "
                        f"Please fix or remove it via 'gurk remove {plugin}'. "
                        "Skipping upgrade..."
                    )
                    continue
                else:
                    # Skip not installed / remote-only plugins
                    ilogfunc(
                        f"Plugin '{plugin}' is remote-only and not "
                        "installed locally. Skipping upgrade..."
                    )
                continue

            # Skip local-only plugins
            if not plugin_data["registration"]["remote"]:
                ilogfunc(
                    f"Plugin '{plugin}' is local-only and has no remote. Skipping upgrade..."
                )
                continue

            plugin_name = plugin_data["metadata"]["name"]
            plugin_local = plugin_data["registration"]["local"]
            plugin_remote = extract_url(plugin_data["registration"]["remote"])

            # Exclude specified plugins
            if normalized_exclude & {plugin_name, plugin_local, plugin_remote}:
                ilogfunc(f"Excluding plugin '{plugin}' from upgrade.")
                continue

            # See if the current version is already the latest
            if get_latest_version(plugin_remote) == get_local_plugin_version(
                plugin_local
            ):
                ilogfunc(
                    f"Plugin '{extract_url(plugin_remote)}' is already at the latest version. Skipping upgrade..."
                )
                continue

            # Store plugin remote
            plugin_remotes.add(plugin_remote)

        for remote in plugin_remotes:
            # Remove existing plugin (if any)
            try:
                remove_plugin(remote, verbose=args.verbose)
            except ModuleNotFoundError:
                pass

            # Pull specified plugin
            pull_plugin(remote)

    logger.done("Plugin upgrades complete.")
