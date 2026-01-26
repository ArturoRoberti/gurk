from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.common import check_version
from gurk.lib.utils.plugins import (
    GurkArgumentParser,
    get_combined_plugin_registry,
    get_plugin_data,
    pull_plugin,
    remove_plugin,
)
from gurk.lib.utils.remotes import edit_url, is_git_repo, parse_git_ref


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "sources",
        type=str,
        nargs="*",
        help="GitRefs of the plugin sources to pull. Specify desired versions using GitRef syntax (commit/version) or via '<plugin_name>=<version>'. If empty, pull all plugins with remotes that are not installed.",
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Replace existing plugins if they already exist.",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        if not args.sources:
            # No sources specified, pull all plugins with remotes that are not installed
            logger.debug(
                "No specific plugins to pull specified. Pulling all uninstalled plugins with remotes..."
            )
            combined_registry = get_combined_plugin_registry()
            for plugin_name, plugin_entry in combined_registry.items():
                if not plugin_entry.get("remote"):
                    continue  # No remote to pull from

                # Check if plugin is already validly installed
                try:
                    get_plugin_data(plugin_name)
                    logger.debug(
                        f"Plugin '{plugin_name}' is already installed. Skipping..."
                    )
                    continue
                except ModuleNotFoundError:
                    pass

                # Remove any existing invalid plugin if --replace is given
                if args.replace:
                    try:
                        remove_plugin(plugin_name)
                        logger.warning(
                            f"Existing invalid plugin '{plugin_name}' removed."
                        )
                    except ModuleNotFoundError:
                        logger.debug(
                            f"No existing invalid plugin '{plugin_name}' to remove."
                        )

                # Pull plugin
                source = plugin_entry["remote"]
                if not pull_plugin(source):
                    logger.error(
                        f"Failed to pull plugin '{plugin_name}' from '{source}'."
                    )
                    continue
                else:
                    logger.info(
                        f"Successfully pulled plugin '{plugin_name}' from '{source}'."
                    )
        else:
            # Extract versions from specified plugins
            logger.debug("Pulling specified plugins...")
            parsed_sources = []
            for source in args.sources:
                count = source.count("=")
                if count == 1:
                    # Get plugin version via CLI syntax
                    plugin_spec, version = (source.split("=", 1) + [None])[:2]
                    if version and not check_version(version):
                        logger.error(
                            f"Invalid version '{version}' for plugin '{plugin_spec}'. Skipping..."
                        )
                        continue

                    # Check that an actual GitRef is given
                    if not is_git_repo(plugin_spec):
                        logger.error(
                            f"'{plugin_spec}' is either not a GitRef or "
                            "points to an inexistent repository. Skipping..."
                        )
                        continue

                    # Get plugin version via GitRef syntax
                    parsed = parse_git_ref(source)
                    if parsed["version"] and not check_version(
                        parsed["version"]
                    ):
                        logger.error(
                            f"Invalid version '{parsed['version']}' for "
                            f"plugin '{source}' in GitRef. Skipping..."
                        )
                        continue

                    # Check for version mismatches
                    if (
                        parsed["version"]
                        and version
                        and parsed["version"] != version
                    ):
                        logger.error(
                            f"Version mismatch for plugin '{source}': GitRef "
                            f"version '{parsed['version']}' does not match "
                            f"specified version '{version}'. Skipping..."
                        )
                        continue
                    else:
                        # Same version - append plugin with specified version
                        parsed_sources.append(
                            edit_url(
                                source, "version", parsed["version"] or version
                            )
                        )

                elif count > 1:
                    logger.error(
                        f"Invalid plugin specification '{source}'. Only one "
                        "'=' is allowed to specify version. Skipping..."
                    )
                else:
                    # Append plugin as-is
                    parsed_sources.append(source)

            # Pull plugins
            for source in parsed_sources:
                if args.remove:
                    # Remove existing plugin (if any)
                    try:
                        remove_plugin(source)
                        logger.warning(
                            f"Existing plugin from source '{source}' removed."
                        )
                    except ModuleNotFoundError:
                        logger.debug(
                            f"No existing plugin from source '{source}' to remove."
                        )
                else:
                    # Check if plugin already exists
                    try:
                        get_plugin_data(source)
                        logger.error(
                            f"Plugin from source '{source}' already exists. "
                            "Use --replace to replace existing plugins."
                        )
                        continue
                    except ModuleNotFoundError:
                        pass

                # Pull specified plugin
                if not pull_plugin(source):
                    logger.error(
                        f"Failed to pull plugin from source '{source}'."
                    )
                    continue
                else:
                    logger.info(
                        f"Successfully pulled plugin from source '{source}'."
                    )

        logger.done("Plugin pulling complete.")
