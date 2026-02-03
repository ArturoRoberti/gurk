import shutil
from pathlib import Path

from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.common import PACKAGE_HOME_PATH
from gurk.lib.utils.configs import dump_yaml, load_yaml
from gurk.lib.utils.plugins import (
    GurkArgumentParser,
    PluginRegistryEntry,
    _get_plugin_registration,
    _get_plugin_registries,
    remove_plugin,
)
from gurk.lib.utils.remotes import is_git_repo
from gurk.lib.utils.typed_dict import validate_typed_dict


def main(argv, prog, description):
    parser = GurkArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "plugins",
        type=str,
        nargs="*",
        help="Names of the plugins to remove",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Purge plugin data completely instead of just removing local paths.",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        for plugin_name in args.plugins:
            # Only allow plugin names
            if is_git_repo(plugin_name) or Path(plugin_name).exists():
                logger.fatal(
                    f"Invalid plugin specification '{plugin_name}' given "
                    f"for removal. Only plugin names are allowed."
                )
                continue

            # Exclude gurk plugin, as it should not be removed
            if plugin_name == "gurk":
                logger.info(
                    "Skipping removal of core 'gurk' plugin, which cannot be removed."
                )
                continue

            # Attempt removal
            try:
                remove_plugin(plugin_name, purge=args.purge, verbose=True)
            except ModuleNotFoundError as e:
                logger.error(str(e))

        # Prompt to remove invalid plugins if any exist
        if not args.non_interactive:
            ## Load home registry
            home_registry_file = _get_plugin_registries(
                package_registry=False
            )[0]
            home_registry = load_yaml(home_registry_file)
            if home_registry is None:
                logger.error(
                    "Failed to load home plugin registry for cleanup."
                )
                return

            ## Invalid plugin entries (local path does not exist)
            invalid_entries: list[str] = []
            for name, entry in home_registry.items():
                if not validate_typed_dict(entry, PluginRegistryEntry) or (
                    entry["local"] is not None
                    and not (
                        home_registry_file.parent / entry["local"]
                    ).is_dir()
                ):
                    invalid_entries.append(name)

            ## Invalid plugin directories (no registry entry)
            invalid_dirs: list[Path] = []
            plugins_base_dir = PACKAGE_HOME_PATH / "plugins"
            if plugins_base_dir.is_dir():
                for item in plugins_base_dir.iterdir():
                    if item.is_dir() and not all(
                        _get_plugin_registration(item, package_registry=False)
                    ):
                        invalid_dirs.append(item)
                    elif item.is_file() and not item.name == "registry.yaml":
                        invalid_dirs.append(item)

            ## Prompt user for cleanup
            if invalid_entries or invalid_dirs:
                # Entries
                if invalid_entries:
                    msg = "The following plugins have invalid structure or local paths:"
                    for name in invalid_entries:
                        msg += f"\n- {name}"

                    if invalid_dirs:
                        msg += "\n\n"

                # Dirs
                if invalid_dirs:
                    msg = "The following plugin directories/files are invalid (no registry entry):"
                    for path in invalid_dirs:
                        msg += f"\n- {str(path)}"

                logger.warning(msg)
                if logger.prompt_bool("Remove these invalid plugins?"):
                    # Entries
                    for name in invalid_entries:
                        del home_registry[name]
                    if invalid_entries:
                        dump_yaml(home_registry, home_registry_file)

                    # Dirs
                    for path in invalid_dirs:
                        if path.is_dir():
                            shutil.rmtree(path)
                        elif path.is_file():
                            path.unlink()

                    logger.info("Invalid plugins removed successfully.")

        logger.done("Plugin removals completed.")
