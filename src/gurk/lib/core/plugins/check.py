from argparse import ArgumentTypeError
from copy import deepcopy
from pathlib import Path
from typing import get_type_hints

import networkx as nx

from gurk.lib.core.context import get_logger
from gurk.lib.core.context.registry_manager import get_plugin_registration
from gurk.lib.utils.common import PathLike, check_version, typecheck
from gurk.lib.utils.configs import load_toml, load_yaml
from gurk.lib.utils.patterns import PatternCollection
from gurk.lib.utils.remotes import is_git_repo
from gurk.lib.utils.scripts import (
    ScriptBlockTypes,
    check_script_blocks,
    get_block_spans,
)
from gurk.lib.utils.tasks import DefaultTaskDictCollection
from gurk.lib.utils.typed_dict import full_isinstance, print_typed_dict_types

from .common import (
    GURK_MANIFEST_FILENAME,
    FilteredPluginMetadata,
    PluginManifest,
    PluginMetadata,
    PluginMetadataDependencies,
    PluginOptions,
)
from .gurk_argparser import GurkArgumentParser, check_args_dict


@typecheck
def filter_metadata(metadata: dict) -> FilteredPluginMetadata | None:
    """
    Return a filtered version of the PluginMetadata containing only relevant fields.

    :param metadata: Raw pyproject.toml metadata dictionary (top-level `pyproject.toml` content)
    :type metadata: dict
    :return: Filtered PluginMetadata
    :rtype: FilteredPluginMetadata
    """
    if not isinstance(metadata, dict):
        return None

    # 'Project' section
    project_data = metadata.get("project")
    if not project_data or not isinstance(project_data, dict):
        return None

    # Allow other fields, thus filter them out before validating
    filtered_metadata = {
        k.replace("-", "_"): v
        for k, v in project_data.items()
        if k.replace("-", "_") in get_type_hints(PluginMetadata)
    }
    filtered_metadata["optional_dependencies"] = {
        k: v
        for k, v in project_data.get("optional-dependencies", {}).items()
        if k in get_type_hints(PluginMetadataDependencies)
    }

    # Validate structure
    if not full_isinstance(filtered_metadata, PluginMetadata):
        return None

    # Version
    if not check_version(filtered_metadata["version"]):
        return None

    # Dependencies
    optional_deps = filtered_metadata.pop("optional_dependencies", {})
    filtered_metadata["dependencies"] = optional_deps.get("gurk", [])

    return filtered_metadata


@typecheck
def check_local_plugin(plugin_path: PathLike, verbose: bool = False) -> bool:
    """
    Check if a local plugin is valid.
        NOTE: All imported plugins (recursively) must also be local and valid.

    :param plugin_path: Path to the local plugin directory
    :type plugin_path: PathLike
    :param verbose: Whether to print errors
    :type verbose: bool
    :return: True if the plugin is valid, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Directed graphs for checking cycles
    imports_graph = nx.DiGraph()
    task_dependency_graph = nx.DiGraph()
    task_supercedes_graph = nx.DiGraph()

    # Save available tasks
    available_tasks: DefaultTaskDictCollection = dict()

    def _check_local_plugin(_plugin_path: Path) -> bool:
        def error(message: str) -> bool:
            msg = f"'{_plugin_path}': {message}"
            if verbose:
                logger.error(msg)
            else:
                logger.debug(msg)

        # Load pyproject.toml
        pyproject_file = _plugin_path / "pyproject.toml"
        if not pyproject_file.is_file():
            error(
                f"Plugin source '{_plugin_path}' is missing a 'pyproject.toml' file."
            )
            return False
        pyproject_data = load_toml(pyproject_file)
        if not pyproject_data:
            error(
                f"Plugin source '{_plugin_path}' has an invalid 'pyproject.toml' file"
            )
            return False

        # Validate pyproject.toml
        project_metadata = filter_metadata(pyproject_data)
        if not project_metadata:
            error(
                f"Plugin source '{_plugin_path}' has an invalid 'pyproject.toml' "
                "file: invalid 'project' section structure. Expected:\n"
                f"{print_typed_dict_types(PluginMetadata, indent=2, as_str=True)}"
            )
            return False

        ## Valid and unique plugin name
        plugin_name = project_metadata["name"]
        if not plugin_name:
            error(
                f"Plugin source '{_plugin_path}' has an invalid "
                "'pyproject.toml' file: 'project.name' is missing or empty."
            )
            return False
        elif not PatternCollection.NAMING.patterns.match(plugin_name):
            error(
                f"Plugin name '{plugin_name}' is invalid: No "
                "special characters except '_' or '-' are allowed."
            )
            return False

        existing_plugin_registration = get_plugin_registration(
            plugin_name,
            home_registry=True,
            package_registry=True,
            require_local=False,
        )
        existing_plugin_entry = (
            next(iter(existing_plugin_registration.values()))
            if existing_plugin_registration
            else None
        )
        if existing_plugin_registration and (
            existing_plugin_entry.get("local") is not None
            and existing_plugin_entry["local"] != _plugin_path.resolve()
        ):
            existing_local = (
                existing_plugin_entry.get("local")
                if existing_plugin_entry
                else None
            )
            error(
                f"Plugin name '{plugin_name}' is already used by another plugin "
                f"at {existing_local if existing_local else '<no local path>'}."
            )
            return False

        # Load manifest file
        plugin: PluginManifest = load_yaml(
            _plugin_path / GURK_MANIFEST_FILENAME
        )
        if plugin is None:
            error(
                f"Plugin source '{_plugin_path}' has no '{GURK_MANIFEST_FILENAME}' file or it is invalid YAML."
            )
            return False

        # Validate structure
        plugin_without_helpers = {
            k: v
            for k, v in plugin.items()
            if isinstance(k, str) and not k.startswith("_")
        }
        if not full_isinstance(plugin_without_helpers, PluginManifest):
            error(
                f"Plugin at '{_plugin_path}' has invalid structure. Expected: "
                f"{print_typed_dict_types(PluginManifest, indent=2, as_str=True)}"
            )
            return False

        ## Check each task field
        plugin_tasks = plugin.get("tasks", {})
        for task_name, task in plugin_tasks.items():
            # Check task name
            plugin_prefix, remaining = (task_name.split("/", 1) + [None])[:2]
            if plugin_prefix != plugin_name or not remaining:
                error(
                    f"Task '{task_name}' has an invalid name. Its "
                    f"name should be '{plugin_name}/<task_name>'"
                )
                return False
            elif not PatternCollection.NAMING.patterns.match(remaining):
                error(
                    f"Task '{task_name}' has an invalid name: No "
                    "special characters except '_' or '-' are allowed."
                )
                return False

            # Check task description
            if not task["description"]:
                error(f"Task '{task_name}' description is missing or empty.")
                return False

            # Check 'script' field
            ## Existence
            script = _plugin_path / task["script"]
            if not script.is_file():
                error(
                    f"Task '{task_name}' script file '{script}' does not exist."
                )
                return False
            ## Validity
            errors = check_script_blocks(script)
            if errors:
                error(
                    f"Task '{task_name}' script '{script}' has errors:\n"
                    + "\n".join(errors)
                )
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
                f_or_e = (
                    ("function " + task["function"])
                    if task["function"]
                    else "entrypoint"
                )
                error(
                    f"Task '{task_name}' {f_or_e} does not exist in script '{script}'."
                )
                return False

            # Check 'config_file' field
            if task.get("config_file") is not None:
                config_file = _plugin_path / task["config_file"]
                if not config_file.is_file():
                    error(
                        f"Task '{task_name}' config file '{config_file}' does not exist."
                    )
                    return False

            # Check 'args' field
            task_args = task.get("args")
            if task_args:
                # Validate structure
                try:
                    check_args_dict(task_args)
                except ArgumentTypeError as e:
                    error(
                        f"Task '{task_name}' has invalid 'args' definition: {e}"
                    )
                    return False

                # Validate arg names
                arg_start = f"--{plugin_name}-"
                arg_names = [arg_name for arg_name in task_args.keys()]
                invalid_args = [
                    arg_name
                    for arg_name in arg_names
                    if not arg_name.startswith(arg_start)
                ]
                if invalid_args:
                    error(
                        f"Task '{task_name}' has an invalid arg names {invalid_args}. "
                        f"Arg names must be '{arg_start}<remaining>'."
                    )
                    return False

        # Check that the 'imports' section is valid
        imports = plugin.get("imports", [])
        if not isinstance(imports, list) or not all(
            isinstance(imp, str) for imp in imports
        ):
            error(
                f"Plugin 'imports' section is not a list of strings, but of type '{type(imports)}'."
            )
            return False

        def _check_graph_cycles(graph: nx.DiGraph, field: str) -> bool:
            """
            Check for cycles in a directed graph.

            :param graph: The directed graph to check
            :type graph: nx.DiGraph
            :param field: The field being checked (for logging purposes)
            :type field: str
            :return: True if no cycles are found, False otherwise
            :rtype: bool
            """
            try:
                cycle = nx.find_cycle(graph)
                if cycle:
                    error(
                        f"Circular dependency detected in '{field}' field: {cycle}"
                    )
                    return False
            except nx.NetworkXNoCycle:
                # No cycle detected
                pass
            return True

        ## Check that imported plugins exist and are valid
        imports_graph.add_node(plugin_name)
        for imp in imports:
            # Check that imported plugins exist in the desired location
            if not get_plugin_registration(
                imp, home_registry=True, package_registry=True
            ):
                msg = f"Imported plugin '{imp}' does not exist locally."
                if is_git_repo(imp):
                    msg += f" You can pull it via 'gurk pull {imp}'."
                error(msg)
                return False

            # Check the imports graph for cycles
            imports_graph.add_edge(plugin_name, imp)
            if not _check_graph_cycles(imports_graph, "imports"):
                return False

            # Check imported plugin
            imp_registration = get_plugin_registration(
                imp, home_registry=True, package_registry=True
            )
            imp_local = next(iter(imp_registration.values()))["local"]
            if not _check_local_plugin(imp_local):
                error(f"Imported plugin '{imp}' is invalid.")
                return False

        # Add defined tasks to available tasks
        task_names = list(plugin_tasks.keys())
        available_tasks.update(plugin_tasks)

        def expand_graph(graph: nx.DiGraph, field: str) -> bool:
            """
            Expand a directed graph with edges from a task field.
                NOTE: The direction is the same, as this is only used for cycle detection.

            :param graph: The directed graph to expand
            :type graph: nx.DiGraph
            :param field: The field from which to add edges
            :type field: str
            :return: True if successful, False if an unknown task is found
            :rtype: bool
            """
            graph.add_nodes_from(task_names)
            for task_name, task in plugin_tasks.items():
                for dep in task.get(field, []):
                    if dep not in available_tasks:
                        error(
                            f"Task '{task_name}' uses unknown "
                            f"task '{dep}' in '{field}' field."
                        )
                        return False
                    graph.add_edge(task_name, dep)

            return True

        # Check the task dependency graph
        dependency_field = "depends_on"
        if not expand_graph(task_dependency_graph, dependency_field):
            return False
        elif not _check_graph_cycles(task_dependency_graph, dependency_field):
            return False

        # Check the task supercedes graph
        supercedes_field = "supercedes"
        if not expand_graph(task_supercedes_graph, supercedes_field):
            return False
        elif not _check_graph_cycles(task_supercedes_graph, supercedes_field):
            return False

        # Check 'options' section
        options: PluginOptions = plugin["options"]
        if "default" not in options:
            error(
                "Plugin 'options' section is missing required 'default' option."
            )
            return False

        ## Validate each option
        for option_name, option in options.items():
            # Check option name
            if "/" in option_name or ":" in option_name:
                error(
                    f"Option name '{option_name}' is invalid. Option names cannot contain '/' or ':'."
                )
                return False

            # Check that all tasks in the option are defined
            for task_name in option.keys():
                if task_name not in available_tasks:
                    error(
                        f"Task '{task_name}' in '{option_name}' option "
                        "is not defined in this or any imported plugins."
                    )
                    return False

            # Check 'config_file' fields
            for task_name, task_spec in option.items():
                config_file = task_spec.get("config_file")
                if config_file:
                    config_file = _plugin_path / task_spec["config_file"]
                    if not config_file.is_file():
                        error(
                            f"Task '{task_name}' in option '{option_name}' "
                            f"config file '{config_file}' does not exist."
                        )
                        return False

            # Check that all args in the option are defined
            for task_name, task_spec in option.items():
                # Create a temporary parser to validate args
                parser = GurkArgumentParser(
                    add_verbose_arg=False,
                    add_non_interactive_arg=False,
                    add_force_arg=True,
                )
                allowed_args = available_tasks[task_name].get("args", {})
                parser.extend_arguments(allowed_args)

                # Override parser.error to raise exception instead of exiting
                def raise_error(message):
                    raise ValueError(message)

                parser.error = raise_error

                # Validate args
                try:
                    parser.parse_args(task_spec.get("args", []))
                except ValueError as e:
                    error(e)
                    return False

            # Determine enabled tasks (including dependencies)
            directly_enabled_tasks = set(option.keys())
            enabled_tasks = deepcopy(directly_enabled_tasks)
            for task_name in directly_enabled_tasks:
                enabled_tasks.update(
                    nx.descendants(task_dependency_graph, task_name)
                )

            # Check that at least one task is being run
            if not enabled_tasks:
                error(f"Option '{option_name}' has no enabled tasks.")
                return False

            # If any tasks are defined in the plugin, that at least one of them must be enabled
            if plugin_tasks and not set(plugin_tasks.keys()) & enabled_tasks:
                error(
                    f"Option '{option_name}' does not enable "
                    "any tasks defined in this plugin."
                )
                return False

            # Check that no two tasks that supercede each other are enabled together
            for u, v in task_supercedes_graph.edges():
                if u in enabled_tasks and v in enabled_tasks:
                    error(
                        f"Tasks '{u}' and '{v}' that supercede each other "
                        f"would both be enabled in the '{option_name}' option"
                    )
                    return False

        # All checks passed
        return True

    # Check plugin
    return _check_local_plugin(Path(plugin_path))
