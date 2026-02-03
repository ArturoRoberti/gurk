from pathlib import Path

from gurk.lib.logger import ActiveLogger, Logger, get_logger
from gurk.lib.utils.common import check_version
from gurk.lib.utils.configs import load_toml
from gurk.lib.utils.plugins import (
    GurkArgumentParser,
    PluginSpec,
    get_plugin_data,
    pull_local_plugin,
    pull_plugin,
    remove_plugin,
)
from gurk.lib.utils.remotes import edit_url, is_git_repo, parse_git_ref


def maybe_remove_existing_plugin(
    plugin_spec: PluginSpec, replace: bool
) -> bool:
    """
    Remove existing plugin if it exists.

    :param plugin_spec: Specification of the plugin to remove.
    :type plugin_spec: PluginSpec
    :param replace: Whether to replace existing plugins.
    :type replace: bool
    """
    # Get logger
    logger = get_logger()

    if replace:
        # Remove existing plugin (if any)
        try:
            remove_plugin(plugin_spec)
        except ModuleNotFoundError:
            logger.debug(f"No existing plugin '{plugin_spec}' to remove.")
    else:
        # Check if plugin already exists
        try:
            get_plugin_data(plugin_spec)
            logger.error(
                f"Plugin '{plugin_spec}' already exists. "
                "Use --replace to replace existing plugins."
            )
            return False
        except ModuleNotFoundError:
            pass

    return True


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "sources",
        type=str,
        nargs="+",
        help="GitRefs of the plugin sources to pull. Specify desired versions using GitRef syntax (commit/version) or via '<plugin_name>=<version>'. If empty, pull all plugins with remotes that are not installed.",
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Replace existing plugins if they already exist.",
    )
    parser.add_argument(
        "-i",
        "--ignore-imports",
        action="store_true",
        help="Do not pull imported plugins.",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        # Extract versions from specified plugins
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
                if parsed["version"] and not check_version(parsed["version"]):
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
                            source, version=(parsed["version"] or version)
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
            # Exclude gurk plugin, as it should be managed via pipx
            try:
                plugin_data = get_plugin_data(source)
                plugin_name = plugin_data["metadata"]["name"]
                if plugin_name == "gurk":
                    logger.info(
                        "Skipping pull of core 'gurk' plugin. Please upgrade 'gurk' separately via 'pipx upgrade gurk'."
                    )
                    continue
            except ModuleNotFoundError:
                pass

            # Handle source type
            if Path(source).is_dir():  # Local plugin directory
                # Get plugin name
                try:
                    plugin_metadata = load_toml(
                        Path(source) / "pyproject.toml"
                    )
                    plugin_name = plugin_metadata["project"]["name"]
                except Exception as e:
                    logger.error(
                        f"Failed to load plugin name from local path '{source}': {str(e)}. Skipping..."
                    )
                    continue

                # Remove existing plugin (if any, and if '--replace' specified)
                if not maybe_remove_existing_plugin(plugin_name, args.replace):
                    continue

                # Pull specified local plugin
                if not pull_local_plugin(source, not args.ignore_imports):
                    logger.error(
                        f"Failed to pull local plugin from path '{source}'."
                    )
                    continue

            elif is_git_repo(source):  # GitRef source
                # Remove existing plugin (if any, and if '--replace' specified)
                if not maybe_remove_existing_plugin(source, args.replace):
                    continue

                # Pull specified plugin
                if not pull_plugin(source, not args.ignore_imports):
                    logger.error(
                        f"Failed to pull plugin from source '{source}'."
                    )
                    continue

            else:
                logger.error(
                    f"'{source}' is either not a GitRef or points to an inexistent repository. Skipping..."
                )
                continue

        logger.done("Plugin pulling complete.")
