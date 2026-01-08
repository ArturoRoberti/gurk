# TODO: Move to util/plugin.py instead of plugin/utils.py? Probably better if not, right? Then move other utils out too, and update docs accordingly.

# TODO: Have one common ArgumentDefaultsHelpFormatter formatter_class and import it everywhere instead
import importlib
import inspect
import shutil
from argparse import (
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    _SubParsersAction,
)
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
from typing import Any, NotRequired, TypedDict, get_args, get_origin

import networkx as nx
from ruamel.yaml import YAML

from gurk.cli.utils import CORE_COMMANDS
from gurk.utils.common import (
    PACKAGE_HOME_PATH,
    PACKAGE_SRC_PATH,
    FilePath,
    generate_random_path,
)
from gurk.utils.remotes import GitRef, clone_git_repo, is_git_repo
from gurk.utils.scripts import (
    ScriptBlockTypes,
    check_script_blocks,
    get_block_spans,
)
from gurk.utils.tasks import (
    CustomConfig,
    CustomTaskDict,
    DefaultConfig,
    TaskDictCollection,
    fill_missing_properties,
)
from gurk.utils.validate import validate_typed_dict, validate_typed_dict_keys
from gurk.utils.yaml import load_yaml

#########################################################################################
#################################### Minor utilities ####################################
#########################################################################################


class PluginDefine(TypedDict):
    # fmt: off
    name:        str
    description: str
    tasks:       NotRequired[DefaultConfig]
    # TODO: Add version field? Maybe also author etc.?
    # fmt: on


class PluginRun(TypedDict):
    options: NotRequired[dict[str, CustomConfig]]
    default: CustomConfig


class GurkPlugin(TypedDict):
    # fmt: off
    imports: NotRequired[list[GitRef | str]]
    define:  PluginDefine
    run:     PluginRun
    # fmt: on


class PluginRegistryEntry(TypedDict):
    local: str
    remote: GitRef | None
    # version: str # Keep? How to read remote repo versions?


def get_plugin_dirs() -> tuple[Path, Path]:
    """
    Get a tuple of plugin directories.

    :return: Tuple of plugin directories (home, package)
    :rtype: tuple[Path, Path]
    """
    possible_plugin_paths = [
        p / "plugins" for p in [PACKAGE_HOME_PATH, PACKAGE_SRC_PATH]
    ]
    for p in possible_plugin_paths:
        p.mkdir(parents=True, exist_ok=True)

    return tuple(possible_plugin_paths)


def get_plugin_registries() -> tuple[Path, Path]:
    """
    Get a tuple of plugin registries.

    :return: Tuple of plugin registries (home, package)
    :rtype: tuple[Path, Path]
    """
    possible_plugin_registries = [
        p / "registry.yaml" for p in get_plugin_dirs()
    ]
    for p in possible_plugin_registries:
        p.touch(exist_ok=True)

    return tuple(possible_plugin_registries)


def get_combined_plugin_registry() -> dict[str, PluginRegistryEntry]:
    """
    Get the combined plugin registry from home and package registries.

    :return: Combined plugin registry
    :rtype: dict[str, PluginRegistryEntry]
    """
    home_registry_file, package_registry_file = get_plugin_registries()
    home_registry = load_yaml(home_registry_file) or {}
    package_registry = load_yaml(package_registry_file) or {}

    # Combine registries, prioritizing home registry
    combined_registry = package_registry.copy()
    combined_registry.update(home_registry)

    return combined_registry


def get_possible_plugin_data(
    plugin: GitRef | str,
) -> tuple[PluginRegistryEntry | None, PluginRegistryEntry | None]:
    """
    Get possible plugin paths for a given plugin name.

    :param plugin: Name or GitRef of the plugin
    :type plugin: GitRef | str
    :return: List of possible plugin paths
    :rtype: list[Path]
    """

    def _load_plugin(
        plugin_dir: Path, registry_file: Path
    ) -> PluginRegistryEntry | None:
        registry: dict[str, PluginRegistryEntry] = (
            load_yaml(registry_file) or {}
        )

        # Get plugin entry
        if plugin in registry:
            # Access plugin by name
            entry = registry[plugin]
        elif any(plugin == v.get("remote") for v in registry.values()):
            # Access plugin by remote
            entry = next(
                v for v in registry.values() if plugin == v.get("remote")
            )
        else:
            return None

        # Validate structure
        if not validate_typed_dict(entry, PluginRegistryEntry):
            print(
                f"Invalid plugin registry entry for plugin '{plugin}' in registry '{registry_file}'."
            )
            return None

        # Resolve local path
        local_path = plugin_dir / entry["local"]
        if not local_path.is_dir():
            print(
                f"Local path '{local_path}' for plugin '{plugin}' does not exist or is not a directory."
            )
            return None
        elif not (local_path / "gurk-plugin.yaml").is_file():
            print(
                f"Local path '{local_path}' for plugin '{plugin}' is missing 'gurk-plugin.yaml' file."
            )
            return None
        entry["local"] = str(local_path)

        return entry

    return tuple(
        _load_plugin(plugin_dir, registry_file)
        for plugin_dir, registry_file in zip(
            get_plugin_dirs(), get_plugin_registries()
        )
    )


def get_plugin_data(plugin: GitRef | str) -> PluginRegistryEntry | None:
    """
    Get the data of a plugin (path, remote) if it exists locally.

    :param plugin: Name or GitRef of the plugin
    :type plugin: GitRef | str
    :return: Plugin data if the plugin exists locally, None otherwise
    :rtype: PluginRegistryEntry | None
    """
    possible_plugin_data = get_possible_plugin_data(plugin)
    plugin_data = tuple(p for p in possible_plugin_data if p is not None)
    return plugin_data[0] if plugin_data else None


def plugin_exists_locally(plugin: GitRef | str) -> bool:
    """
    Check if a plugin exists in the possible local plugin paths.

    :param plugin: Name or GitRef of the plugin
    :type plugin: GitRef | str
    :return: True if the plugin exists locally, False otherwise
    :rtype: bool
    """
    return get_plugin_data(plugin) is not None


def plugin_exists_remotely(plugin: GitRef) -> bool:
    """
    Check if a plugin exists in the possible remote plugin paths.

    :param plugin: GitRef of the plugin
    :type plugin: GitRef
    :return: True if the plugin exists remotely, False otherwise
    :rtype: bool
    """
    return is_git_repo(plugin)


def plugin_exists(plugin: GitRef | str) -> bool:
    """
    Check if a plugin exists either locally or remotely.

    :param plugin: Name or URL of the plugin
    :type plugin: GitRef | str
    :return: True if the plugin exists, False otherwise
    :rtype: bool
    """
    return plugin_exists_locally(plugin) or plugin_exists_remotely(plugin)


def get_plugin_config(plugin: GitRef | str) -> GurkPlugin | None:
    """
    Get the gurk-plugin.yaml configuration of a plugin if it exists locally.

    :param plugin: Name or GitRef of the plugin
    :type plugin: GitRef | str
    :return: GurkPlugin configuration if the plugin exists locally, None otherwise
    :rtype: GurkPlugin | None
    """
    plugin_data = get_plugin_data(plugin)
    if not plugin_data:
        return None

    if not check_local_plugin(plugin_data["local"]):
        return None

    return load_yaml(Path(plugin_data["local"]) / "gurk-plugin.yaml")


def combine_plugin_configs(
    plugins: list[GitRef | str],
) -> dict[str, GurkPlugin]:
    """
    Combine the gurk-plugin.yaml configurations of multiple plugins.

    :param plugins: List of plugin names or GitRefs
    :type plugins: list[GitRef | str]
    :return: Dictionary of plugin names to GurkPlugin configurations
    :rtype: dict[str, GurkPlugin]
    """
    combined_configs: TaskDictCollection = {}
    for plugin in plugins:
        plugin_config = get_plugin_config(plugin)
        if plugin_config:
            # Get tasks
            tasks = plugin_config["define"]["tasks"]

            # Fill missing properties
            plugin_tasks = fill_missing_properties(tasks, default=True)

            # Expand paths
            plugin_path = get_plugin_data(plugin)["local"]
            for _, task in tasks.items():
                # Expand script path
                task["script"] = str(Path(plugin_path) / task["script"])

                # Expand config_file path (if applicable)
                if task["config_file"] is not None:
                    task["config_file"] = str(
                        Path(plugin_path) / task["config_file"]
                    )

            combined_configs.update(plugin_tasks)

    return combined_configs


def add_plugin_entry(
    plugin_name: str, plugins_entry: PluginRegistryEntry
) -> bool:
    """
    Add a plugin to the home plugin registry.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :param plugins_entry: Plugin registry entry
    :type plugins_entry: PluginRegistryEntry
    :return: True if the plugin was added successfully, False otherwise
    :rtype: bool
    """
    # Load home plugin registry
    registry_file = get_plugin_registries()[0]  # Home registry
    registry: dict[str, PluginRegistryEntry] = load_yaml(registry_file) or {}

    # Check if plugin already exists
    if plugin_name in registry:
        return False

    # Add plugin entry
    registry[plugin_name] = {
        "local": plugins_entry["local"],
        "remote": plugins_entry["remote"],
    }
    with open(registry_file, "w") as f:
        YAML().dump(registry, f)

    return True


def remove_plugin_entry(plugin_name: str) -> None:
    """
    Remove a plugin from the home plugin registry.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    """
    # Load home plugin registry
    registry_file = get_plugin_registries()[0]  # Home registry
    registry: dict[str, PluginRegistryEntry] = load_yaml(registry_file) or {}

    # Check if plugin exists
    if plugin_name not in registry:
        return

    # Remove plugin entry
    del registry[plugin_name]
    with open(registry_file, "w") as f:
        YAML().dump(registry, f)


#########################################################################################
################################### Command utilities ###################################
#########################################################################################


def create_subparser(subparsers: _SubParsersAction, module_name: str) -> None:
    """
    Create a subparser for the given module name.

    :param subparsers: The subparsers action to add the subparser to
    :type subparsers: _SubParsersAction
    :param module_name: The module name to import
    :type module_name: str
    """
    # Find all *_cmd functions
    module = importlib.import_module(module_name)
    for func_name, func in inspect.getmembers(module, inspect.isfunction):
        if func_name.endswith("_cmd"):
            # Add subparser
            cmd_description = (func.__doc__ or "").strip().splitlines()[0]
            parser_cmd: ArgumentParser = subparsers.add_parser(
                func_name.replace("_cmd", ""),
                description=cmd_description,
                help=cmd_description,
                formatter_class=lambda prog: ArgumentDefaultsHelpFormatter(
                    prog=prog,
                    max_help_position=60,
                ),
            )

            # Inspect the function signature
            sig = inspect.signature(func)
            args_param = None
            if sig.parameters:
                # Only take the first parameter
                first_param = next(iter(sig.parameters.values()))
                args_type = first_param.annotation
                if is_dataclass(args_type):
                    args_param = args_type

            # Add arguments dynamically from dataclass if present
            if args_param:
                for field in fields(args_param):
                    origin = get_origin(field.type)
                    args = {}

                    # ---- LIST TYPES ----
                    if origin is list:
                        name = field.name
                        args["type"] = get_args(field.type)[0]

                        if (
                            field.default is not MISSING
                            or field.default_factory is not MISSING
                        ):
                            # Optional positional list
                            args["nargs"] = "*"

                            if field.default is not MISSING:
                                # default
                                args["default"] = field.default
                            else:
                                # default_factory
                                args["default"] = field.default_factory()
                        else:
                            # Required positional list
                            args["nargs"] = "+"

                    # ---- BOOL FLAGS ----
                    elif field.type is bool:
                        name = f"--{field.name.replace('_', '-')}"
                        if field.default is MISSING or field.default is False:
                            # 'False' by default
                            args["action"] = "store_true"
                        elif field.default is True:
                            # 'True' by default
                            args["action"] = "store_false"
                        else:
                            raise ValueError(
                                f"Boolean field '{field.name}' has invalid default value."
                            )

                    # ---- SCALAR TYPES ----
                    else:
                        args["type"] = field.type
                        if field.default is MISSING:
                            # positional argument
                            name = field.name
                        else:
                            # optional argument
                            name = f"--{field.name.replace('_', '-')}"
                            args["default"] = field.default

                    # ---- HELP TEXT ----
                    if "help" in field.metadata:
                        args["help"] = field.metadata["help"]

                    parser_cmd.add_argument(name, **args)

            # Set the function to call
            parser_cmd.set_defaults(func=func)


def check_local_plugin(
    plugin_path: FilePath,
    check_imports: bool = False,
    require_local: bool = False,
) -> bool:
    """
    Check if a local plugin is valid.

    :param plugin_path: Path to the local plugin
    :type plugin_path: FilePath
    :param check_imports: Whether to check imported plugins as well, if locally available (default: False)
    :type check_imports: bool, optional
    :param require_local: Whether to require imported plugins to be available locally (default: False)
    :type require_local: bool, optional
    :return: True if the plugin is valid, False otherwise
    :rtype: bool
    """
    plugin_graph = nx.DiGraph()

    def _check_local_plugin(_plugin_path: str) -> bool:
        # Load gurk-plugin.yaml
        plugin = load_yaml(Path(_plugin_path) / "gurk-plugin.yaml")
        if not plugin:
            print(
                f"Plugin source '{_plugin_path}' has no 'gurk-plugin.yaml' file or it is invalid YAML."
            )
            return False

        # Add plugin node to graph
        plugin_graph.add_node(_plugin_path)

        # Validate top-level structure
        plugin_without_helpers = {
            k: v
            for k, v in plugin.items()
            if isinstance(k, str) and not k.startswith("_")
        }
        if not validate_typed_dict_keys(plugin_without_helpers, GurkPlugin):
            print("Plugin has invalid top-level keys.")
            # TODO: Use logger (error)
            return False

        # Check that the 'define' section is valid
        plugin_definition: PluginDefine = plugin.get("define")
        if not plugin_definition:
            # TODO: Use logger (error)
            print("Plugin has no 'define' section.")
            return False

        ## Fill missing task properties and validate structure
        plugin_definition["tasks"] = fill_missing_properties(
            plugin_definition["tasks"], default=True
        )
        if not validate_typed_dict(plugin_definition, PluginDefine):
            print("Plugin 'define' section has invalid structure.")
            # TODO: Use logger (error)
            return False

        ## Check that 'script', 'function, and 'config_file' exist where applicable
        for task_name, task in plugin_definition["tasks"].items():
            # Check task name
            command, remaining = (task_name.split("-", 1) + [None])[:2]
            if not remaining:
                print(
                    f"Task '{task_name}' has no command prefix (expected: '<command>-<taskname>', with <command> in {CORE_COMMANDS})."
                )
                # TODO: Use logger (error)
                return False
            elif command not in CORE_COMMANDS:
                print(
                    f"Task '{task_name}' has invalid command prefix '{command}'. Valid commands are: {CORE_COMMANDS}."
                )

            # Check 'script' field
            ## Existence
            script = Path(_plugin_path) / task["script"]
            if not script.is_file():
                print(
                    f"Task '{task_name}' script file '{script}' does not exist."
                )
                # TODO: Use logger (error)
                return False
            ## Validity
            errors = check_script_blocks(script)
            if errors:
                print(
                    f"Task '{task_name}' script '{script}' has errors:\n"
                    + "\n".join(errors)
                )
                # TODO: Use logger (error)
                return False

            # Check 'function' field
            blocks = get_block_spans(script)
            if task["function"] is None:
                desired_block_type = ScriptBlockTypes.ENTRYPOINT
            else:
                desired_block_type = ScriptBlockTypes.FUNCTION
            if not any(
                b["name"] == task["function"]
                for b in blocks
                if b["type"] == desired_block_type
            ):
                print(
                    f"Task '{task_name}' {'function ' + task['function'] if task['function'] else 'entrypoint'} does not exist in script '{script}'."
                )
                # TODO: Use logger (error)
                return False

            # Check 'config_file' field
            if task["config_file"] is not None:
                config_file = Path(_plugin_path) / task["config_file"]
                if not config_file.is_file():
                    print(
                        f"Task '{task_name}' config file '{config_file}' does not exist."
                    )
                    # TODO: Use logger (error)
                    return False

        # Check that the 'run' section is valid
        plugin_run: PluginRun = plugin.get("run")
        if not plugin_run:
            print("Plugin has no 'run' section.")
            # TODO: Use logger (error)
            return False

        def fill_tasks_only(
            incomplete_tasks: dict[str, Any]
        ) -> dict[str, Any]:
            # Filter out flags
            flags = {
                k: v
                for k, v in incomplete_tasks.items()
                if isinstance(v, bool)
            }

            # Fill only tasks
            tasks_only = {
                k: v
                for k, v in incomplete_tasks.items()
                if isinstance(v, dict)
            }
            remaining_keys = [
                k
                for k in incomplete_tasks.keys()
                if k not in flags and k not in tasks_only
            ]
            if any(remaining_keys):
                print(
                    f"Default 'run' section has invalid entries that are neither tasks nor flags: {remaining_keys}"
                )
                # TODO: Use logger (fatal)
            incomplete_tasks = fill_missing_properties(
                tasks_only, default=False
            )

            # Add flags back
            incomplete_tasks.update(flags)
            return incomplete_tasks

        ## Fill missing properties in tasks in 'default' option
        plugin_run_default = plugin_run.get("default")
        if not plugin_run_default or not isinstance(plugin_run_default, dict):
            print(
                "Plugin 'run' section 'default' field is missing or invalid."
            )
            # TODO: Use logger (error)
            return False
        plugin_run["default"] = fill_tasks_only(plugin_run_default)

        ## Fill missing properties in tasks in other options
        options = plugin_run.get("options", {})
        if not isinstance(options, dict):
            print("Plugin 'run' section 'options' field is not a dictionary.")
        elif options:
            for option_name, option in options.items():
                options[option_name] = fill_tasks_only(option)

        ## Validate structure after filling in missing task properties
        if not validate_typed_dict(plugin_run, PluginRun):
            print("Plugin 'run' section has invalid structure.")
            # TODO: Use logger (error)
            return False

        ## Test that any tasks are being run in each option/default
        for option in [
            plugin_run["default"],
            *plugin_run.get("options", {}).values(),
        ]:
            if not option.get("enable_all") and not any(
                validate_typed_dict(v, CustomTaskDict) and v["enabled"]
                for k, v in option.items()
            ):
                print(
                    "Plugin 'run' section has an option with no tasks being run."
                )
                # TODO: Use logger (error)
                return False

        # Check that the 'imports' section is valid
        imports = plugin.get("imports", [])
        if not isinstance(imports, list) or not all(
            isinstance(imp, str) for imp in imports
        ):
            print(
                f"Plugin 'imports' section is not a list of strings, but of type '{type(imports)}'."
            )
            # TODO: Use logger (error)
            return False

        ## Check that imported plugins exist and if so, add to dependency graph
        for imp in imports:
            # Check that imported plugins exist in the desired location
            if not plugin_exists(imp):
                print(
                    f"Imported plugin '{imp}' does not exist locally or remotely."
                )
                # TODO: Use logger (fatal)
                return False

            if require_local and not plugin_exists_locally(imp):
                print(f"Imported plugin '{imp}' is not available locally.")
                # TODO: Use logger (fatal)
                return False

            # Check imported plugin
            if check_imports:
                plugin_data = get_plugin_data(imp)
                if plugin_data:
                    # Add node and edge
                    plugin_graph.add_node(imp)
                    plugin_graph.add_edge(_plugin_path, imp)

                    # Avoid circular imports
                    try:
                        cycle = nx.find_cycle(
                            plugin_graph, orientation="original"
                        )
                        if cycle:
                            raise ValueError(
                                f"Circular plugin dependency detected: {cycle}"
                            )
                    except nx.NetworkXNoCycle:
                        # No cycle detected
                        pass

                    # Check imported plugin
                    return _check_local_plugin(plugin_data["local"])

        # All checks passed
        return True

    # Check plugin
    return _check_local_plugin(str(plugin_path))


def import_plugin(plugin: GitRef | str, update: bool = False) -> bool:
    """
    Import a plugin from a remote Git repository.

    :param plugin: GitRef of the plugin to import
    :type plugin: GitRef | str
    :param update: Whether to update existing plugins if they already exist (default: False)
    :type update: bool, optional
    :return: True if the plugin was imported successfully, False otherwise
    :rtype: bool
    """

    def error(message: str, _temp_plugin_path: Path | None = None):
        print(message + ". Skipping...")  # TODO: Use logger (error)
        if _temp_plugin_path is not None:
            shutil.rmtree(_temp_plugin_path)

    # Import plugin to temporary directory
    temp_plugin_path = generate_random_path(
        prefix="gurk_plugin_import_", create=False
    )
    if Path(plugin).is_dir():
        # Local folder
        source_is_local = True
        shutil.copytree(plugin, temp_plugin_path)
    elif is_git_repo(plugin):
        # Git repo
        source_is_local = False
        clone_git_repo(plugin, temp_plugin_path)
    else:
        error(
            f"Source '{plugin}' is neither a local directory nor a valid git repository"
        )
        return False

    # Check that the plugin is valid
    try:
        check_local_plugin(temp_plugin_path)
    except SystemExit:
        error(
            f"Plugin at '{plugin}' is invalid and cannot be imported",
            temp_plugin_path,
        )
        return False

    # Load gurk-plugin.yaml
    gurk_plugin: GurkPlugin = load_yaml(Path(plugin) / "gurk-plugin.yaml")
    if not gurk_plugin:
        error(
            f"Plugin at '{plugin}' is missing a valid 'gurk-plugin.yaml' file and cannot be imported",
            temp_plugin_path,
        )
        return False

    # Check if plugin with same name already exists
    plugin_name = gurk_plugin["define"]["name"]
    if get_plugin_data(plugin_name):
        if not update:
            error(
                f"Plugin '{plugin_name}' already exists. Use '--update' to replace it.",
                temp_plugin_path,
            )
            return False
        else:
            remove_plugin(plugin_name)
            print(
                f"Plugin '{plugin_name}' already exists. Replacing it..."
            )  # TODO: Use logger (info)

    # Add plugin
    plugin_path = PACKAGE_HOME_PATH / "plugins" / plugin_name
    ## Add plugin folder
    shutil.move(temp_plugin_path, plugin_path)
    ## Add plugin registry entry
    add_plugin_entry(
        plugin_name,
        PluginRegistryEntry(
            local=str(plugin_path),
            remote=None if source_is_local else plugin,
        ),
    )


# TODO: Cache it before deleting it. How to specify version tough?
def remove_plugin(plugin_name: str) -> None:
    """
    Remove plugins from local installation.

    :param args: RemoveArgs dataclass instance
    :type args: RemoveArgs
    """
    # Get plugin data
    plugin_data = get_plugin_data(plugin_name)
    if not plugin_data:
        print(f"Plugin '{plugin_name}' is not installed.")
        return

    # Remove plugin folder
    plugin_path = Path(plugin_data["local"])
    if plugin_path.is_dir():
        shutil.rmtree(plugin_path)

    # Remove plugin registry entry
    remove_plugin_entry(plugin_name)
