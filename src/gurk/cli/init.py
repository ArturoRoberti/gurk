from gurk.lib.context import GurkContext, Logger, get_registries
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    create_plugin_venv,
    get_venv_gurk_version,
    install_plugin,
    is_plugin_installed,
    remove_venv,
    venv_exists,
)
from gurk.lib.utils import GURK_VERSION


def main(argv, prog, description):
    parser = GurkArgumentParser[DefaultNamespace](
        prog=prog, description=description
    )
    args = parser.parse_args(argv)

    # Execute with writing to plugins
    with GurkContext(
        logger=Logger(args.verbose, args.non_interactive), writable=True
    ) as ctx:
        combined_registry = get_registries(
            home_registry=True, package_registry=True, combine=True
        )
        for plugin_name, plugin_entry in combined_registry.items():
            # Remove plugin venv (if any) with different gurk version
            if (
                venv_exists(plugin_name)
                and get_venv_gurk_version(plugin_name) != GURK_VERSION
            ):
                ctx.logger.debug(
                    f"Removing existing virtual environment for plugin '{plugin_name}' to ensure it is re-created with the current gurk version."
                )
                if not remove_venv(plugin_name):
                    ctx.logger.error(
                        f"Failed to remove existing virtual environment for plugin '{plugin_name}'."
                    )
                    return False

            # Check if plugin is already validly installed
            if not is_plugin_installed(plugin_name, require_venv=False):
                if plugin_entry.get("remote"):
                    # Pull plugin (and remove any existing invalid plugin) if not installed
                    source = plugin_entry["remote"]
                    ctx.logger.debug(
                        f"Plugin '{plugin_name}' is not installed. Pulling from remote '{source}'..."
                    )
                    if not install_plugin(source, reinstall=True):
                        ctx.logger.error(
                            f"Failed to pull plugin '{plugin_name}' from '{source}'."
                        )
                        continue
                else:
                    ctx.logger.warning(
                        f"Local plugin '{plugin_name}' is not validly installed. Please remove it manually."
                    )
                    continue

            # CHECK: Plugin should now be installed
            if not is_plugin_installed(plugin_name, require_venv=False):
                ctx.logger.error(
                    f"Unexpected: Plugin '{plugin_name}' is still not installed."
                )
                continue

            # Create plugin venv
            if plugin_name != "gurk" and not venv_exists(plugin_name):
                if not create_plugin_venv(plugin_name):
                    ctx.logger.error(
                        f"Failed to create virtual environment for plugin '{plugin_name}'",
                    )
                    continue

        ctx.logger.done("Initialization complete.")
