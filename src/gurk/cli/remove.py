import shutil
from pathlib import Path

from gurk.lib.context import (
    GurkContext,
    Logger,
    get_plugin_directories,
    get_registries,
    get_registry_files,
    is_plugin_registered,
)
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    remove_plugin,
)
from gurk.lib.shared.remotes import is_git_repo


class RemoveNamespace(DefaultNamespace):
    plugins: list[str] | None


def main(argv, prog, description):
    parser = GurkArgumentParser[RemoveNamespace](
        prog=prog, description=description
    )
    group = parser.add_required_group()
    group.add_argument(
        "plugins",
        type=str,
        nargs="*",
        help="Names of the registered plugins to remove",
    )
    args = parser.parse_args(argv)

    # Execute with writing to plugins
    with GurkContext(
        logger=Logger(
            verbose=args.verbose,
            non_interactive=args.non_interactive,
            description="Removing plugins",
        ),
        writable=True,
    ) as ctx:
        for plugin_name in args.plugins:
            # Only allow plugin names
            if Path(plugin_name).exists() or is_git_repo(plugin_name):
                ctx.logger.error(
                    f"Invalid plugin specification '{plugin_name}' given "
                    f"for removal. Only plugin names are allowed."
                )
                continue

            # Exclude package plugins, as they should not be removed
            package_registry = get_registries(
                home_registry=False, package_registry=True
            )
            if plugin_name in package_registry:
                registry_file = get_registry_files(
                    home_registry=False, package_registry=True
                )
                ctx.logger.error(
                    f"Cannot remove '{plugin_name}', as it is a package plugin. If "
                    "you really want to remove this plugin, you can manually set "
                    f"its local path to 'null' in {registry_file.as_posix()}."
                )
                continue

            # Attempt removal
            try:
                remove_plugin(plugin_name, verbose=True)
            except ModuleNotFoundError as e:
                ctx.logger.error(str(e))

        # Prompt to remove invalid plugins if any exist
        if not args.non_interactive:
            ## Collect unregistered paths
            unregistered_paths: set[Path] = set()
            for dir, is_home in zip(get_plugin_directories(), [True, False]):
                for item in dir.iterdir():
                    if item.is_dir() and not is_plugin_registered(
                        item,
                        home_registry=is_home,
                        package_registry=not is_home,
                    ):
                        unregistered_paths.add(item)
                    elif item.is_file() and not item.name == "registry.yaml":
                        unregistered_paths.add(item)

            ## Prompt user for cleanup
            if unregistered_paths:
                msg = "The following paths are not registered (thus invalid):"
                for path in unregistered_paths:
                    msg += f"\n- {str(path)}"

                ctx.logger.warning(msg)
                if ctx.logger.prompt_bool("Remove these unregistered paths?"):
                    for path in unregistered_paths:
                        if path.is_dir():
                            shutil.rmtree(path)
                        elif path.is_file():
                            path.unlink()

                    ctx.logger.info("Unregistered paths removed successfully.")

        ctx.logger.done("Plugin removals completed.")
