import shutil
from pathlib import Path

from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    get_plugin_directories,
    get_plugin_registration,
    get_plugin_registries,
    remove_plugin,
)
from gurk.lib.utils.remotes import is_git_repo


class RemoveNamespace(DefaultNamespace):
    plugins: list[str] | None


def main(argv, prog, description):
    parser = GurkArgumentParser[RemoveNamespace](
        prog=prog, description=description
    )
    parser.add_argument(
        "plugins",
        type=str,
        nargs="*",
        help="Names of the plugins to remove",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        for plugin_name in args.plugins:
            # Only allow plugin names
            if Path(plugin_name).exists() or is_git_repo(plugin_name):
                logger.fatal(
                    f"Invalid plugin specification '{plugin_name}' given "
                    f"for removal. Only plugin names are allowed."
                )
                continue

            # Exclude package plugins, as they should not be removed
            package_registry = get_plugin_registries(home_registry=False)[0]
            if plugin_name in package_registry:
                logger.info(
                    f"Skipping removal of package plugin '{plugin_name}', which cannot be removed."
                )
                continue

            # Attempt removal
            try:
                remove_plugin(plugin_name, verbose=True)
            except ModuleNotFoundError as e:
                logger.error(str(e))

        # Prompt to remove invalid plugins if any exist
        if not args.non_interactive:
            ## Collect unregistered paths
            unregistered_paths: set[Path] = set()
            for dir, is_home in zip(get_plugin_directories(), [True, False]):
                for item in dir.iterdir():
                    if item.is_dir() and not all(
                        get_plugin_registration(
                            item,
                            home_registry=is_home,
                            package_registry=not is_home,
                        )
                    ):
                        unregistered_paths.add(item)
                    elif item.is_file() and not item.name == "registry.yaml":
                        unregistered_paths.add(item)

            ## Prompt user for cleanup
            if unregistered_paths:
                msg = "The following paths are not registered (thus invalid):"
                for path in unregistered_paths:
                    msg += f"\n- {str(path)}"

                logger.warning(msg)
                if logger.prompt_bool("Remove these unregistered paths?"):
                    for path in unregistered_paths:
                        if path.is_dir():
                            shutil.rmtree(path)
                        elif path.is_file():
                            path.unlink()

                    logger.info("Unregistered paths removed successfully.")

        logger.done("Plugin removals completed.")
