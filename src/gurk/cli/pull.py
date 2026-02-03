from pathlib import Path
from textwrap import dedent

from termcolor import colored

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
from gurk.lib.utils.remotes import (
    GitRefInfo,
    commit_exists,
    edit_url,
    extract_url,
    is_git_repo,
    parse_git_ref,
    version2commit,
)


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
            remove_plugin(plugin_spec, verbose=True)
        except ModuleNotFoundError:
            pass
    else:
        # Check if plugin already exists
        try:
            get_plugin_data(plugin_spec)
            logger.error(
                f"Some version of plugin '{extract_url(plugin_spec)}' already "
                "exists. Use '--replace' to replace existing plugins."
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
        help=dedent(
            f"""\
            Local paths or partial GitRefs of the plugin sources to pull. Specify desired versions using either of:
            - CLI syntax   : <url>=<version>
            - GitRef syntax: <url>?commit=... OR <url>?version=...
            {colored("WARNING:", "yellow", attrs=["bold"])} Do not use '&' in GitRefs unless quoted, as they will be misinterpreted by the shell.
        """
        ),
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
                # Get plugin version
                ## GitRef syntax
                parsed = parse_git_ref(source)
                if parsed["version"]:
                    version = parsed["version"]
                    commit = None
                    plugin_spec = parsed["url"]
                elif parsed["commit"]:
                    version = None
                    commit = parsed["commit"]
                    plugin_spec = parsed["url"]
                elif any(
                    [
                        parsed[k]
                        for k in GitRefInfo.__annotations__.keys()
                        if k not in ("url", "version", "commit")
                    ]
                ):
                    logger.error(
                        "Cannot specify other GitRef parameters while specifying"
                        "any other than 'version' or 'commit'. Skipping..."
                    )
                    continue
                ## CLI syntax
                else:
                    commit = None
                    plugin_spec, version = parsed["url"].split("=")

                # Check that an actual GitRef is given
                if not is_git_repo(plugin_spec):
                    logger.error(
                        f"'{plugin_spec}' is either not a GitRef or "
                        "points to an inexistent repository. Skipping..."
                    )
                    continue

                if version:
                    # Check that the version conforms to semantic versioning
                    if not check_version(version):
                        logger.error(
                            f"Invalid version '{version}' for plugin "
                            f"'{source}' in GitRef. Skipping..."
                        )
                        continue

                    # Check that the specified version exists
                    if not version2commit(plugin_spec, version):
                        logger.error(
                            f"Version '{version}' for plugin "
                            f"'{plugin_spec}' does not exist. Skipping..."
                        )
                        continue

                    # Edit plugin spec to include version
                    plugin_spec = edit_url(plugin_spec, version=version)
                elif commit:
                    # Check that the commit exists
                    if not commit_exists(plugin_spec, commit):
                        logger.error(
                            f"Commit '{commit}' for plugin "
                            f"'{plugin_spec}' does not exist. Skipping..."
                        )
                        continue

                    # Edit plugin spec to include commit
                    plugin_spec = edit_url(plugin_spec, commit=commit)

                # Append plugin with specified version/commit
                parsed_sources.append(plugin_spec)

            elif count > 1:
                logger.error(
                    f"Invalid plugin specification '{source}'. Only one "
                    "'=' is allowed to specify version. Skipping..."
                )
            else:
                # No version specified - Append plugin as-is.
                #   Existence is checked later.
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
                    f"'{source}' points to an inexistent repository. Skipping..."
                )
                continue

        logger.done("Plugin pulling complete.")
