from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    create_plugin_venv,
    get_combined_plugin_registry,
    install_plugin,
    is_plugin_installed,
    plugin_venv_exists,
)


def main(argv, prog, description):
    parser = GurkArgumentParser[DefaultNamespace](
        prog=prog, description=description
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        combined_registry = get_combined_plugin_registry()
        for plugin_name, plugin_entry in combined_registry.items():
            # Check if plugin is already validly installed
            if is_plugin_installed(plugin_name, require_venv=True):
                logger.debug(
                    f"Plugin '{plugin_name}' is already installed. Skipping..."
                )
                continue
            elif not is_plugin_installed(plugin_name, require_venv=False):
                if plugin_entry.get("remote"):
                    # Pull plugin (and remove any existing invalid plugin) if not installed
                    source = plugin_entry["remote"]
                    logger.debug(
                        f"Plugin '{plugin_name}' is not installed. Pulling from remote '{source}'..."
                    )
                    if not install_plugin(source, reinstall=True):
                        logger.error(
                            f"Failed to pull plugin '{plugin_name}' from '{source}'."
                        )
                        continue
                    else:
                        logger.info(
                            f"Successfully pulled plugin '{plugin_name}' from '{source}'."
                        )
                else:
                    logger.warning(
                        f"Local plugin '{plugin_name}' is not validly installed. Please remove it manually."
                    )
                    continue

            # CHECK: Plugin should now be installed
            if not is_plugin_installed(plugin_name, require_venv=False):
                logger.error(
                    f"Unexpected: Plugin '{plugin_name}' is still not installed."
                )
                continue

            # Create plugin venv if necessary
            if not plugin_venv_exists(plugin_name) and plugin_name != "gurk":
                # Create venv
                if not create_plugin_venv(plugin_name):
                    logger.error(
                        f"Failed to create virtual environment for plugin '{plugin_name}'",
                    )
                    continue
                else:
                    logger.info(
                        f"Successfully created venv for local plugin '{plugin_name}'."
                    )

        logger.done("Initialization complete.")
