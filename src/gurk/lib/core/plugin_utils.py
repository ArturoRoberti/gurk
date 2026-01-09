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
from typing import NotRequired, TypedDict, get_args, get_origin

import networkx as nx
from ruamel.yaml import YAML

from gurk.lib.utils.common import (
    PACKAGE_HOME_PATH,
    PACKAGE_SRC_PATH,
    FilePath,
    generate_random_path,
)
from gurk.lib.utils.remotes import GitRef, clone_git_repo, is_git_repo
from gurk.lib.utils.scripts import (
    ScriptBlockTypes,
    check_script_blocks,
    get_block_spans,
)
from gurk.lib.utils.tasks import (
    CustomTaskDict,
    CustomTaskDictCollection,
    DefaultTaskDict,
    DefaultTaskDictCollection,
    TaskDictCollection,
    fill_missing_properties,
)
from gurk.lib.utils.validate import validate_typed_dict
from gurk.lib.utils.yaml import load_yaml

#########################################################################################
#################################### Minor utilities ####################################
#########################################################################################


class PluginDefine(TypedDict):
    # fmt: off
    name:        str
    description: str
    tasks:       NotRequired[DefaultTaskDictCollection]
    # TODO: Add version field? Maybe also author etc.?
    # fmt: on


class PluginRun(TypedDict):
    options: NotRequired[dict[str, CustomTaskDictCollection]]
    default: CustomTaskDictCollection


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


def _get_plugin_dirs() -> tuple[Path, Path]:
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


def _get_plugin_registries() -> tuple[Path, Path]:
    """
    Get a tuple of plugin registries.

    :return: Tuple of plugin registries (home, package)
    :rtype: tuple[Path, Path]
    """
    possible_plugin_registries = [
        p / "registry.yaml" for p in _get_plugin_dirs()
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
    home_registry_file, package_registry_file = _get_plugin_registries()
    home_registry = load_yaml(home_registry_file) or {}
    package_registry = load_yaml(package_registry_file) or {}

    # Combine registries, prioritizing home registry
    combined_registry = package_registry.copy()
    combined_registry.update(home_registry)

    return combined_registry


def _get_possible_plugin_data(
    plugin: GitRef | str,
) -> tuple[PluginRegistryEntry | None, PluginRegistryEntry | None]:
    """
    Get possible plugin paths for a given plugin name.
        NOTE: This does not check the validity of the plugin yaml file.

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
            _get_plugin_dirs(), _get_plugin_registries()
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
    possible_plugin_data = _get_possible_plugin_data(plugin)
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


def load_plugin_yaml(plugin: GitRef | str) -> GurkPlugin | None:
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


def get_available_plugin_names() -> list[str]:
    """
    Get the names of all available local plugins.

    :return: List of available local plugin names
    :rtype: list[str]
    """
    combined_registry = get_combined_plugin_registry()
    return list(combined_registry.keys())


# TODO: Test new name prefix
def get_combined_plugin_tasks() -> dict[str, DefaultTaskDict]:
    """
    Get the combined task definitions of all local plugins.

    :return: Dictionary of tasks from all local plugins
    :rtype: dict[str, DefaultTaskDict]
    """
    combined_tasks: TaskDictCollection = {}
    for plugin in get_available_plugin_names():
        plugin_yaml = load_plugin_yaml(plugin)
        if plugin_yaml:
            # Get tasks and fill missing properties
            tasks = plugin_yaml["define"]["tasks"]
            tasks = fill_missing_properties(tasks, default=True)

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

            combined_tasks.update(tasks)

    return combined_tasks


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
    registry_file = _get_plugin_registries()[0]  # Home registry
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
    registry_file = _get_plugin_registries()[0]  # Home registry
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


# TODO: Remove
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


# TODO: Remaining checks from TaskProcessor:
#       - Check dependency and supercedes graphs ('define' section)
#       - Check that args passed are valid ('run' section)
# TODO: Improve error messages
#       - The plugin path should be prefixed in all messages
#       - Use logger instead of print
#       - Be more informative in general (e.g., which fields are missing/invalid, and how they are invalid / to fix them)
#       - Maybe collect all errors and print them at the end instead of exiting at the first error
def check_local_plugin(plugin_path: FilePath) -> bool:
    """
    Check if a local plugin is valid.
        NOTE: All imported plugins (recursively) must also be local and valid.

    :param plugin_path: Path to the local plugin
    :type plugin_path: FilePath
    :return: True if the plugin is valid, False otherwise
    :rtype: bool
    """
    # Persistent data
    plugin_graph = nx.DiGraph()
    available_task_names: set[str] = set()

    def _check_local_plugin(_plugin_path: Path) -> bool:
        # Load gurk-plugin.yaml
        plugin: GurkPlugin = load_yaml(_plugin_path / "gurk-plugin.yaml")
        if not plugin:
            print(
                f"Plugin source '{_plugin_path}' has no 'gurk-plugin.yaml' file or it is invalid YAML."
            )
            return False

        # Add plugin node to graph
        plugin_graph.add_node(_plugin_path)

        # Validate structure
        plugin_without_helpers: GurkPlugin = {
            k: v
            for k, v in plugin.items()
            if isinstance(k, str) and not k.startswith("_")
        }
        if not validate_typed_dict(plugin_without_helpers, GurkPlugin):
            print(f"Plugin '{_plugin_path}' has invalid structure.")
            # TODO: Find a way to be more informative. Maybe print required structure, similar to before?
            # TODO: Use logger (error)
            return False

        ## Check that the plugin name is unique
        plugin_definition: PluginDefine = plugin["define"]
        plugin_name = plugin_definition["name"]
        existing_plugin = get_plugin_data(plugin_name)
        if existing_plugin and Path(existing_plugin["local"]) != _plugin_path:
            print(
                f"Plugin name '{plugin_name}' is already used by another plugin at '{existing_plugin['local']}'."
            )
            # TODO: Use logger (error)
            return False

        ## Check plugin description
        min_description_length = 10
        if len(plugin_definition["description"]) < min_description_length:
            print(
                f"Plugin '{plugin_name}' description is too short. Please provide a more "
                f"detailed description (at least {min_description_length} characters)."
            )

        ## Check each task field
        for task_name, task in plugin_definition["tasks"].items():
            # Check task name
            plugin_prefix, remaining = (task_name.split("/", 1) + [None])[:2]
            if plugin_prefix != plugin_definition["name"] or not remaining:
                print(
                    f"Task '{task_name}' has an invalid name. Its name should be '{plugin_definition['name']}/<task_name>'"
                )
                # TODO: Use logger (error)
                return False

            # Check task description
            if len(task["description"]) < min_description_length:
                print(
                    f"Task '{task_name}' description is too short. Please provide a more "
                    f"detailed description (at least {min_description_length} characters)."
                )

            # Check 'script' field
            ## Existence
            script = _plugin_path / task["script"]
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
            if task.get("config_file") is not None:
                config_file = _plugin_path / task["config_file"]
                if not config_file.is_file():
                    print(
                        f"Task '{task_name}' config file '{config_file}' does not exist."
                    )
                    # TODO: Use logger (error)
                    return False

            # TODO: Check that default args are allowed. This can be removed if the new args structure is implemented

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
            if not plugin_exists_locally(imp):
                msg = f"Imported plugin '{imp}' does not exist locally."
                if plugin_exists_remotely(imp):
                    msg += f" You can pull it via 'gurk pull {imp}'."
                print(msg)
                # TODO: Use logger (fatal)
                return False

            # Add node and edge
            plugin_graph.add_node(imp)
            plugin_graph.add_edge(_plugin_path, imp)

            # Avoid circular imports
            try:
                cycle = nx.find_cycle(plugin_graph, orientation="original")
                if cycle:
                    raise ValueError(
                        f"Circular plugin dependency detected: {cycle}"
                    )
            except nx.NetworkXNoCycle:
                # No cycle detected
                pass

            # Check imported plugin
            return _check_local_plugin(Path(get_plugin_data(imp)["local"]))

        # Add defined tasks to available tasks
        available_task_names.update(plugin_definition["tasks"].keys())

        # Check 'run' section
        plugin_run: PluginRun = plugin["run"]
        for option in [
            plugin_run["default"],
            *plugin_run.get("options", {}).values(),
        ]:
            # Check that all tasks in the option are defined
            for task_name in option.keys():
                if task_name not in available_task_names:
                    print(
                        f"Task '{task_name}' in 'run' section is not defined in this or any imported plugins."
                    )
                    return False

            # Check that at least one task is being run.
            # If any tasks are defined in the plugin, that at least one of them must be enabled
            if not any(
                validate_typed_dict(v, CustomTaskDict)
                and v["enabled"]
                and (
                    not plugin_definition.get("tasks")
                    or k.split("/", 1)[0] == plugin_definition["name"]
                )
                for k, v in option.items()
            ):
                print(
                    "Plugin 'run' section has an option with no tasks (or none from this plugin, if defined) being run."
                )
                # TODO: Use logger (error)
                return False

        # All checks passed
        return True

    # Check plugin
    return _check_local_plugin(Path(plugin_path))


# TODO: Make 'update' default to True?
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
