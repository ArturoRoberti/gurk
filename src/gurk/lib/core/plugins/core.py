import shutil
import subprocess
from pathlib import Path

from gurk.lib.core.context import get_logger
from gurk.lib.core.context.registry_manager import (
    get_plugin_directories,
    get_plugin_registration,
    get_registries,
    is_plugin_registered,
    update_registry,
)
from gurk.lib.core.plugins.virtual_environments import (
    create_venv,
    remove_venv,
    venv_exists,
)
from gurk.lib.utils.common import PathLike, check_version, generate_random_path
from gurk.lib.utils.configs import load_toml, load_yaml
from gurk.lib.utils.remotes import (
    GIT_QUERY_VERSIONING_FIELDS,
    GitQuery,
    determine_ref,
    edit_url,
    extract_url,
    git_clone,
    is_git_repo,
    parse_git_query,
)

from .check import check_local_plugin
from .common import (
    GURK_MANIFEST_FILENAME,
    PluginManifest,
    PluginSource,
    PluginSpecification,
    PluginSpecificationEnum,
)
from .getters import get_plugin_data
from .versioning import get_plugin_commit

#########################################################################################
#################################### Minor utilities ####################################
#########################################################################################


# TODO: Version/commit check?
def is_plugin_installed(
    plugin: PluginSpecification, *, require_venv: bool = True
) -> bool:
    """
    Check if a plugin is validly installed, optionally requiring that its venv exists.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :param require_venv: Whether to check if the plugin's virtual environment exists
    :type require_venv: bool
    :return: True if the plugin is installed (and its venv exists if require_venv is True), False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check that the plugin is validly installed
    try:
        plugin_data = get_plugin_data(plugin)
    except ModuleNotFoundError as e:
        if is_plugin_registered(
            plugin, home_registry=True, package_registry=True
        ):
            logger.debug(
                f"Plugin '{plugin}' is installed but invalid ({e}) - please fix or remove it"
            )
        else:
            logger.debug(f"Plugin '{plugin}' is not installed.")
        return False

    # Check that the plugin venv exists
    if require_venv and not venv_exists(plugin_data["metadata"]["name"]):
        logger.debug(
            f"Plugin '{plugin}' is installed but its venv is missing."
        )
        return False

    return True


#########################################################################################
################################### Command utilities ###################################
#########################################################################################


def create_plugin_venv(plugin_name: str) -> bool:
    """
    Create a virtual environment for a plugin based on its dependencies in pyproject.toml.

    :param plugin_name: Name of the plugin
    :type plugin_name: str
    :return: True if the virtual environment was created successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check if plugin exists locally
    if not is_plugin_installed(plugin_name, require_venv=False):
        logger.error(
            f"Plugin '{plugin_name}' is not installed - Cannot create virtual environment."
        )
        return False

    # Get plugin dependencies
    dependencies = get_plugin_data(plugin_name)["metadata"]["dependencies"]

    # Create plugin venv
    return create_venv(plugin_name, dependencies)


def _install_local_plugin(plugin_path: PathLike) -> bool:
    """
    Import a plugin from a local directory.

    :param plugin_path: Path to the local plugin directory
    :type plugin_path: PathLike
    :return: True if the plugin was imported successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Get plugin manifest
    plugin_path = Path(plugin_path)
    manifest_data: PluginManifest = load_yaml(
        plugin_path / GURK_MANIFEST_FILENAME
    )
    if not manifest_data:
        logger.error(
            f"Plugin at '{plugin_path}' has no '{GURK_MANIFEST_FILENAME}' file or it is empty/invalid YAML",
        )
        return False

    # Get plugin metadata
    metadata = load_toml(plugin_path / "pyproject.toml")
    if not metadata:
        logger.error(
            f"Plugin at '{plugin_path}' has an invalid or missing 'pyproject.toml' file",
        )
        return False

    # Extract plugin name from metadata
    try:
        plugin_name: str = metadata["project"]["name"]
    except KeyError as e:
        logger.error(
            f"Plugin at '{plugin_path}' has an invalid 'pyproject.toml' file: missing key {e}",
        )
        return False

    # Check if plugin with same name already exists
    if is_plugin_registered(
        plugin_name,
        home_registry=True,
        package_registry=True,
        require_local=True,
    ):
        logger.error(
            f"Plugin with name '{plugin_name}' already exists. Please "
            f"remove it via 'gurk remove {plugin_name}' first."
        )
        return False

    # Pull imported plugins recursively
    for imp in manifest_data.get("imports", []):
        if not is_plugin_installed(imp, require_venv=False):
            if not install_plugin(imp):
                logger.error(
                    f"Failed to pull imported plugin '{imp}' for plugin '{plugin_path}'",
                )
                return False
        else:
            logger.debug(
                f"Imported plugin '{imp}' for plugin '{plugin_path}' is already installed. Skipping pull."
            )

    # Check validity of local plugin
    if not check_local_plugin(plugin_path, verbose=True):
        logger.error(
            f"Plugin at '{plugin_path}' is not a valid gurk plugin.",
        )
        return False

    # Add plugin registry entry
    if not update_registry(plugin_name, {"remote": None}, infer_local=True):
        logger.error(
            f"Failed to add plugin '{plugin_name}' to registry after pulling local plugin from '{plugin_path}'",
        )
        return False
    registration = get_plugin_registration(
        plugin_name,
        home_registry=True,
        package_registry=True,
        require_local=False,
    )
    registration_entry = next(iter(registration.values()))
    dest = registration_entry.get("local")
    if not dest:
        logger.error(
            f"Registry entry for plugin '{plugin_name}' has invalid 'local' "
            f"path, although it should have been inferred: {registration_entry}",
        )
        return False

    # Add plugin folder
    if Path(dest).exists():
        logger.warning(
            f"Destination path '{dest}' for plugin '{plugin_name}' already exists. Overwriting it..."
        )
        shutil.rmtree(dest)
    shutil.copytree(plugin_path, dest)

    # Install plugin dependencies in the plugin venv
    if not create_plugin_venv(plugin_name):
        logger.error(
            f"Failed to create virtual environment for plugin '{plugin_name}'",
        )
        return False

    # Verify installation
    if not is_plugin_installed(plugin_name, require_venv=True):
        logger.error(
            f"Plugin '{plugin_name}' installation verification "
            f"failed after pulling local plugin from '{plugin_path}'",
        )
        return False

    return True


# TODO: Check that version/commit specified exists
def _install_remote_plugin(plugin: GitQuery) -> bool:
    """
    Import a plugin from a remote Git repository.

    :param plugin: GitQuery of the plugin to import
    :type plugin: GitQuery
    :return: True if the plugin was imported successfully, False otherwise
    :rtype: bool
    """

    def error(message: str, _temp_path: Path | None = None):
        """
        Log an error message and clean up temporary plugin path if provided.

        :param message: Error message to log
        :type message: str
        :param _temp_path: Temporary plugin path to clean up
        :type _temp_path: Path | None
        """
        get_logger().error(message + ". Skipping...")
        if _temp_path is not None and _temp_path.exists():
            if _temp_path.is_dir():
                shutil.rmtree(_temp_path)
            else:
                _temp_path.unlink()

    # Check that the repo exists
    if not is_git_repo(plugin):
        error(
            f"Remote plugin source '{plugin}' does not exist or is not a valid git repository"
        )
        return False

    # Check that version/commit specified exists
    commit = determine_ref(plugin, to_commit=True)
    if commit is None:
        error(
            f"Specified version/commit in remote plugin source '{plugin}' does not exist"
        )
        return False

    # Import metadata to random file
    temp_metadata = generate_random_path(suffix=".toml", create=False)
    try:
        git_clone(edit_url(plugin, path="pyproject.toml"), temp_metadata)
    except subprocess.CalledProcessError as e:
        error(
            f"Failed to clone 'pyproject.toml' from "
            f"remote plugin repository '{plugin}': {e}",
            temp_metadata,
        )
        return False
    except ValueError as e:
        error(str(e), temp_metadata)
        return False

    # Get relevant metadata
    try:
        metadata = load_toml(temp_metadata)
        plugin_name: str = metadata["project"]["name"]
        plugin_version: str = metadata["project"]["version"]
        if not check_version(plugin_version):
            raise ValueError(f"Invalid version string: {plugin_version}")
    except KeyError as e:
        error(
            f"Plugin '{plugin}' has an invalid 'pyproject.toml' file: invalid key {e}",
            temp_metadata,
        )
        return False

    # Check if plugin already exists
    if is_plugin_installed(plugin_name):
        error(
            f"Plugin with remote '{plugin}' is already installed. "
            f"Please remove it via 'gurk remove {plugin_name}' "
            f"first or update it via 'gurk update {plugin_name}'"
        )
        return False

    # See if plugin source is valid
    if not is_git_repo(plugin):
        error(
            f"Remote plugin source '{plugin}' does not exist or is not a valid git repository"
        )
        return False

    # Import manifest to random file
    temp_manifest = generate_random_path(suffix=".yaml", create=False)
    try:
        git_clone(edit_url(plugin, path=GURK_MANIFEST_FILENAME), temp_manifest)
    except subprocess.CalledProcessError as e:
        error(
            f"Failed to clone '{GURK_MANIFEST_FILENAME}' "
            f"from remote plugin repository '{plugin}': {e}",
            temp_manifest,
        )
        return False

    # Determine relevant files
    relevant_files = {GURK_MANIFEST_FILENAME, "pyproject.toml"}
    try:
        # Load manifest file with basic validation
        manifest_data = load_yaml(temp_manifest)
        if not manifest_data:
            raise ValueError("Empty or invalid YAML")

        # Defined tasks
        tasks = manifest_data.get("tasks", {})
        if isinstance(tasks, dict):
            for task in tasks.values():
                if isinstance(task, dict):
                    # Script
                    script = task.get("script")
                    if not isinstance(script, str):
                        raise ValueError(
                            f"Invalid 'script' field in task: {task}"
                        )
                    relevant_files.add(script)

                    # Config file
                    config_file = task.get("config_file")
                    if config_file is not None and not isinstance(
                        config_file, str
                    ):
                        raise ValueError(
                            f"Invalid 'config_file' field in task: {task}"
                        )
                    elif config_file is not None:
                        relevant_files.add(config_file)
                else:
                    raise ValueError(
                        f"Invalid task type in 'tasks': {type(task)} (expected dict)"
                    )
        else:
            raise ValueError(
                f"Invalid 'tasks' section type: {type(tasks)} (expected dict)"
            )

        # Options
        options = manifest_data.get("options", {})
        if isinstance(options, dict):
            for option in options.values():
                if isinstance(option, dict):
                    for task in option.values():
                        # Config file
                        config_file = task.get("config_file")
                        if config_file is not None and not isinstance(
                            config_file, str
                        ):
                            raise ValueError(
                                f"Invalid 'config_file' field in task: {task}"
                            )
                        elif config_file is not None:
                            relevant_files.add(config_file)
                else:
                    raise ValueError(
                        f"Invalid task option type in 'options': {type(option)} (expected dict)"
                    )
        else:
            raise ValueError(
                f"Invalid 'options' section type: {type(options)} (expected dict)"
            )
    except Exception as e:
        error(
            f"Remote plugin repository '{plugin}' has an invalid '{GURK_MANIFEST_FILENAME}' file: {e}",
            temp_manifest,
        )
        return False

    # Clone only relevant files to temporary directory
    temp_plugin_path = generate_random_path(
        prefix="gurk_plugin_import_", create=False
    )
    for file in relevant_files:
        pullfile = edit_url(plugin, path=file)
        try:
            git_clone(pullfile, dest=temp_plugin_path / file)
        except subprocess.CalledProcessError:
            error(
                f"Failed to clone file '{file}' from remote plugin repository '{plugin}'",
                temp_plugin_path,
            )
            return False

    # Pull local plugin from temporary directory
    if not _install_local_plugin(temp_plugin_path):
        error(
            f"Failed to import plugin from remote repository '{plugin}'",
            temp_plugin_path,
        )
        return False

    # Upate plugin registry entry to include remote
    if not update_registry(
        plugin_name,
        {
            "remote": edit_url(
                extract_url(plugin),
                commit=determine_ref(plugin, to_commit=True),
            )
        },
    ):
        error(
            f"Failed to update registry entry for plugin '{plugin_name}' with remote information after pulling from '{plugin}'",
        )
        return False

    # Clean up temporary plugin path
    shutil.rmtree(temp_plugin_path)

    return True


def remove_plugin(plugin: PluginSpecification, verbose: bool = False) -> None:
    """
    Remove a locally installed plugin.

    :param plugin: Name, PathLike, or GitQuery of the plugin to remove
    :type plugin: PluginSpecification
    :param verbose: Whether to print info messages
    :type verbose: bool
    :raises ModuleNotFoundError: If no such local plugin is found
    """
    # Get logger
    logger = get_logger()
    remove_msg = []

    # Get plugin data
    plugin_registration = get_plugin_registration(
        plugin, home_registry=True, package_registry=True, require_local=False
    )
    if not plugin_registration:
        raise ModuleNotFoundError(
            f"No installed plugin called '{plugin}' found"
        )
    plugin_name, plugin_entry = next(iter(plugin_registration.items()))

    # Remove plugin registry entry
    if update_registry(plugin_name, None):
        remove_msg.append("registry entry")

    # Remove plugin folder
    if plugin_entry["local"]:
        plugin_path = Path(plugin_entry["local"])
        if plugin_path.is_dir():
            shutil.rmtree(plugin_path)
        remove_msg.append("plugin files")

    # Remove plugin venv
    if remove_venv(plugin_name):
        remove_msg.append("virtual environment")

    if verbose:
        if remove_msg:
            logger.info(
                f"Successfully removed {' and '.join(remove_msg)} for plugin '{plugin_name}'"
            )
        else:
            logger.info(
                f"Nothing to remove for (package) plugin '{plugin_name}'"
            )

    logger.error(
        logger.pprint_dict(
            get_registries(home_registry=False, package_registry=True),
            as_str=True,
        )
    )


def install_plugin(
    plugin_source: PluginSource, reinstall: bool = False
) -> bool:
    """
    Install a plugin from a specified source, which can be either a local path or a Git URL.

    :param plugin_source: Path or Git URL specifying the plugin source
    :type plugin_source: PluginSource
    :param reinstall: Whether to reinstall the plugin if it is already installed (but does not match the specified source or version).
    :type reinstall: bool
    :return: True if the plugin was (re)installed successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    def unexpected_source_type_error():
        logger.error(
            f"Unexpected: Unknown source type '{source_type}' for source '{plugin_source}'."
        )

    # Check source type
    if Path(plugin_source).is_dir():
        source_type = PluginSpecificationEnum.LOCAL_PATH
    elif is_git_repo(plugin_source):
        source_type = PluginSpecificationEnum.GIT_REMOTE
    else:
        logger.error(
            f"Invalid plugin source '{plugin_source}': Must be either a local "
            "path or a Git Query whose URL points to an existing repository."
        )
        return False

    # Check source and get plugin spec
    if source_type == PluginSpecificationEnum.LOCAL_PATH:
        plugin_path = Path(plugin_source)
        # Check that the local path is not under either plugin directory
        if any(
            plugin_path.is_relative_to(d) for d in get_plugin_directories()
        ):
            logger.error(
                f"Specified local path '{plugin_path}' is invalid: "
                "Local paths cannot be under plugin directories."
            )
            return False

        # Get the plugin name
        try:
            plugin_spec = load_toml(plugin_path / "pyproject.toml")["project"][
                "name"
            ]
        except Exception as e:
            logger.error(
                f"Failed to load plugin name from '{plugin_path}': {str(e)}"
            )
            return False
    elif source_type == PluginSpecificationEnum.GIT_REMOTE:
        # Check that max one of version/commit is specified in the remote URL (if any)
        parsed = parse_git_query(plugin_source)
        if (
            len(
                [
                    f
                    for f in GIT_QUERY_VERSIONING_FIELDS
                    if parsed[f] is not None
                ]
            )
            > 1
        ):
            logger.error(
                f"Invalid Git remote source '{plugin_source}':"
                " Cannot specify more than one of "
                f"{', '.join(GIT_QUERY_VERSIONING_FIELDS)} in the Git remote URL."
            )
            return False
        plugin_spec = plugin_source
    else:
        unexpected_source_type_error()
        return False

    # Utility function to install plugin based on source type
    def _install_plugin() -> bool:
        """
        Install the plugin based on its source type.

        :return: True if the plugin was installed successfully, False otherwise
        :rtype: bool
        """
        logger.info(f"Installing plugin from '{plugin_source}'...")
        if source_type == PluginSpecificationEnum.LOCAL_PATH:
            success = _install_local_plugin(plugin_source)
        elif source_type == PluginSpecificationEnum.GIT_REMOTE:
            success = _install_remote_plugin(plugin_source)
        else:
            unexpected_source_type_error()
            return False

        if success:
            logger.info(
                f"Successfully installed plugin from '{plugin_source}'"
            )
        else:
            logger.error(f"Failed to install plugin from '{plugin_source}'")
        return success

    # Act depending on whether the plugin is already installed
    if not is_plugin_installed(plugin_spec, require_venv=False):
        # Handle existing venv
        if venv_exists(plugin_spec):
            if not reinstall:
                logger.error(
                    f"Plugin '{plugin_spec}' is not currently installed but "
                    "has an existing virtual environment. Pass 'reinstall=True' "
                    "to remove the existing venv and proceed with installation."
                )
                return False
            else:
                logger.debug(
                    f"Removing existing virtual environment for plugin '{plugin_spec}' to proceed with installation..."
                )
                if not remove_venv(plugin_spec):
                    logger.error(
                        f"Failed to remove existing virtual environment for plugin '{plugin_spec}'."
                    )
                    return False

        # Install plugin
        logger.info(
            f"Plugin '{plugin_spec}' is not currently installed - installing it."
        )
        if not _install_plugin():
            return False
    else:
        # Get plugin data
        plugin_data = get_plugin_data(plugin_spec)

        # Determine if the plugin needs to be reinstalled
        reinstall_required = False
        if source_type == PluginSpecificationEnum.LOCAL_PATH:
            if reinstall:
                reinstall_required = True
            else:
                logger.debug(
                    f"ERROR: Plugin '{plugin_spec}' is already installed. Pass 'reinstall=True' to reinstall it."
                )
                return False
        elif source_type == PluginSpecificationEnum.GIT_REMOTE:
            # Check version/commit against existing one if specified
            if not plugin_data["registration"]["remote"]:
                logger.error(
                    f"Plugin '{plugin_spec}' is installed but does not have a "
                    "remote URL registered, so the two plugins are considered "
                    "different. Please change the specification or remove the "
                    f"existing plugin first using 'gurk remove {plugin_spec}'."
                )
                return False
            installed_commit = get_plugin_commit(plugin_spec)
            specified_commit = determine_ref(plugin_spec, to_commit=True)
            if installed_commit != specified_commit:
                if reinstall:
                    reinstall_required = True
                else:
                    msg = (
                        f"Plugin '{plugin_spec}' is installed at a "
                        "different version than specified:\n- specified: "
                    )
                    possibly_specified_commit = determine_ref(
                        plugin_spec, to_commit=False
                    )
                    if specified_commit == possibly_specified_commit:
                        msg += possibly_specified_commit
                    else:
                        specified_ref = determine_ref(
                            plugin_spec, to_commit=False
                        )
                        msg += f"{specified_ref} -> {specified_commit}"
                    logger.error(
                        f"{msg}\n- installed: {installed_commit}\nUse "
                        "'--replace' to reinstall and use the specified version."
                    )
                    return False
        else:
            unexpected_source_type_error()
            return False

        # Reinstall plugin if needed
        if reinstall_required:
            logger.info(
                f"Reinstalling plugin '{plugin_spec}' to match specified commit."
            )
            # Remove existing plugin
            try:
                remove_plugin(plugin_spec, verbose=True)
            except ModuleNotFoundError as e:
                logger.error(str(e))
                return False
            # Install plugin
            if not _install_plugin():
                return False
        else:
            # Install the plugin venv if it doesn't exist
            plugin_name = plugin_data["metadata"]["name"]
            if not venv_exists(plugin_name):
                logger.info(
                    f"Plugin '{plugin_spec}' is already installed but has no virtual environment. Creating venv..."
                )
                if not create_plugin_venv(plugin_name):
                    logger.error(
                        f"Failed to create virtual environment for plugin '{plugin_spec}'."
                    )
                    return False

    return True
