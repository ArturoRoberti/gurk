from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.common import PACKAGE_HOME_PATH
from gurk.lib.utils.plugins import (
    GurkArgumentParser,
    create_plugin_venv,
    get_combined_plugin_registry,
    get_plugin_data,
    pull_plugin,
    remove_plugin,
)


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        # Pull all plugins with remotes that are not installed
        logger.debug("Pulling all uninstalled plugins with remotes...")
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

            # Remove any existing invalid plugin
            try:
                remove_plugin(plugin_name)
                logger.warning(f"Existing plugin '{plugin_name}' removed.")
            except ModuleNotFoundError:
                logger.debug(f"No existing plugin '{plugin_name}' to remove.")

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

        # Create venvs for all local plugins that don't have one yet
        logger.debug(
            "Creating venvs for all local plugins that don't have one yet..."
        )
        combined_registry = get_combined_plugin_registry()
        for plugin_name, plugin_entry in combined_registry.items():
            # Skip plugins that are not local
            if plugin_entry.get("remote"):
                continue
            elif plugin_name == "gurk":
                # Skip gurk core plugin
                continue

            # Check if plugin is already validly installed
            try:
                plugin_data = get_plugin_data(plugin_name)
            except ModuleNotFoundError:
                logger.warning(
                    f"Local plugin '{plugin_name}' is not validly installed."
                )
                continue

            # Check if venv exists
            plugin_venv_path = PACKAGE_HOME_PATH / "venvs" / plugin_name
            if plugin_venv_path.exists():
                logger.debug(
                    f"Venv for local plugin '{plugin_name}' already exists. Skipping..."
                )
                continue

            # Create venv
            if not create_plugin_venv(
                plugin_name, plugin_data["metadata"]["dependencies"]
            ):
                logger.error(
                    f"Failed to create virtual environment for plugin '{plugin_name}'",
                )
                continue
            else:
                logger.info(
                    f"Successfully created venv for local plugin '{plugin_name}'."
                )

        logger.done("Initialization complete.")
