import filecmp
import shutil
import subprocess
from pathlib import Path

from gurk.lib.context import get_logger
from gurk.lib.context.registry import (
    get_plugin_directories,
    get_plugin_registration,
    is_plugin_registered,
    update_registry,
)
from gurk.lib.core.plugins.virtual_environments import (
    create_venv,
    remove_venv,
    venv_exists,
)
from gurk.lib.shared.configs import load_toml, load_yaml
from gurk.lib.shared.plugins import (
    PluginManifest,
    PluginSource,
    PluginSpecification,
    PluginSpecificationEnum,
)
from gurk.lib.shared.remotes import (
    GitQuery,
    determine_ref,
    edit_url,
    extract_url,
    get_latest_version,
    git_clone,
    is_git_repo,
    parse_git_query,
)
from gurk.lib.utils import (
    GIT_QUERY_VERSIONING_FIELDS,
    GURK_MANIFEST_FILENAME,
    GURK_METADATA_FILENAME,
    Comparison,
    PathLike,
    check_version,
    compare_versions,
    generate_random_path,
    typecheck,
)

from .check import check_local_plugin
from .getters import get_plugin_data, get_relevant_plugin_files
from .versioning import (
    get_local_plugin_version,
    get_plugin_commit,
    get_plugin_version,
)


@typecheck
def is_plugin_installed(
    plugin_spec: PluginSpecification, *, require_venv: bool = True
) -> bool:
    """
    Check if a plugin is validly installed, optionally requiring that its venv exists.

    :param plugin_spec: Name, PathLike, or GitQuery of the plugin. If a GitQuery is provided, the plugin is considered installed if a plugin with the same remote URL and version/commit (if specified) is installed.
    :type plugin_spec: PluginSpecification
    :param require_venv: Whether to check if the plugin's virtual environment exists
    :type require_venv: bool
    :return: True if the plugin is installed (and its venv exists if require_venv is True), False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check that the plugin is validly installed
    try:
        plugin_data = get_plugin_data(plugin_spec)
    except ModuleNotFoundError as e:
        if is_plugin_registered(
            plugin_spec, home_registry=True, package_registry=True
        ):
            logger.debug(
                f"Plugin '{plugin_spec}' is installed but invalid ({e}) - please fix or remove it"
            )
        else:
            logger.debug(f"Plugin '{plugin_spec}' is not installed.")
        return False

    # Check that the specified version/commit is installed
    parsed = parse_git_query(str(plugin_spec))
    if any(parsed[f] for f in GIT_QUERY_VERSIONING_FIELDS) and is_git_repo(
        plugin_spec
    ):
        installed_commit = get_plugin_commit(plugin_spec)
        specified_commit = determine_ref(plugin_spec, to_commit=True)
        if installed_commit != specified_commit:
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
                specified_ref = determine_ref(plugin_spec, to_commit=False)
                msg += f"{specified_ref} -> {specified_commit}"
            logger.debug(f"{msg}\n- installed: {installed_commit}")
            return False

    # Check that the plugin venv exists
    if require_venv and not venv_exists(plugin_data["metadata"]["name"]):
        logger.debug(
            f"Plugin '{plugin_spec}' is installed but its venv is missing."
        )
        return False

    return True


@typecheck
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


@typecheck
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
    manifest_file = plugin_path / GURK_MANIFEST_FILENAME
    if not manifest_file.is_file():
        logger.error(
            f"Plugin at '{plugin_path}' has no '{GURK_MANIFEST_FILENAME}' file."
        )
        return False

    # Load manifest data
    manifest_data: PluginManifest = load_yaml(manifest_file)
    if not manifest_data:
        raw_manifest = manifest_file.read_text(
            encoding="utf-8", errors="replace"
        )
        logger.error(
            f"Plugin at '{plugin_path}' has empty/invalid YAML in '{GURK_MANIFEST_FILENAME}': "
            f"Preview (max 100 chars):\n{raw_manifest[:100]}"
        )
        return False

    # Get plugin metadata
    metadata = load_toml(plugin_path / GURK_METADATA_FILENAME)
    if not metadata:
        logger.error(
            f"Plugin at '{plugin_path}' has an invalid or missing '{GURK_METADATA_FILENAME}' file",
        )
        return False

    # Extract plugin name from metadata
    try:
        plugin_name: str = metadata["project"]["name"]
    except KeyError as e:
        logger.error(
            f"Plugin at '{plugin_path}' has an invalid '{GURK_METADATA_FILENAME}' file: missing key {e}",
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
        if not is_plugin_installed(extract_url(imp), require_venv=False):
            if not install_plugin(imp):
                logger.error(
                    f"Failed to pull imported plugin '{imp}' for plugin '{plugin_path}'",
                )
                return False
        else:
            if is_plugin_installed(imp, require_venv=False):
                logger.debug(
                    f"Imported plugin '{imp}' for plugin '{plugin_path}' is already installed. Skipping pull."
                )
            else:
                logger.warning(
                    f"Imported plugin '{imp}' for plugin '{plugin_path}' is already installed "
                    f"but with a different version. Please explicitly pull the desired version "
                    f"via 'gurk pull {imp}' to ensure the correct version is installed."
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
    if dest is None:
        logger.error(
            f"Registry entry for plugin '{plugin_name}' has no local path, "
            f"although it should have been inferred: {registration_entry}",
        )
        return False

    # Add plugin folder
    if dest.exists():
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


@typecheck
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
        git_clone(
            edit_url(plugin, path=GURK_METADATA_FILENAME),
            temp_metadata,
        )
    except subprocess.CalledProcessError as e:
        error(
            f"Failed to clone '{GURK_METADATA_FILENAME}' from "
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
            f"Plugin '{plugin}' has an invalid '{GURK_METADATA_FILENAME}' file: invalid key {e}",
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

    # Clone only relevant files to temporary directory
    relevant_files = get_relevant_plugin_files(plugin, relative=False)
    if relevant_files is None:
        error(
            f"Failed to pull relevant files for plugin '{plugin}' from its remote repository"
        )
        return False
    temp_plugin_path = [
        f for f in relevant_files if f.name == GURK_MANIFEST_FILENAME
    ][0].parent

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
                commit=commit,
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


@typecheck
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
    if plugin_entry["local"] and plugin_entry["local"].is_dir():
        shutil.rmtree(plugin_entry["local"])
        remove_msg.append("plugin files")

    # Remove plugin venv
    if remove_venv(plugin_name):
        remove_msg.append("virtual environment")

    if verbose:
        if remove_msg:
            logger.success(
                f"Successfully removed {' and '.join(remove_msg)} for plugin '{plugin_name}'"
            )
        else:
            logger.info(
                f"Nothing to remove for (package) plugin '{plugin_name}'"
            )


# def compare_plugin_version(plugin_source: PluginSource, plugin_spec: PluginSpecification, require_local: bool = True) -> Comparison | None:
#     """
#     Compare the version of a plugin source to the one of a registered plugin_spec.

#     :param plugin_source: The plugin source to compare, either a local path or a Git URL
#     :type plugin_source: PluginSource
#     :param plugin_spec: The plugin specification to compare against, either a plugin name, a local path, or a Git URL. If a Git URL is provided, the plugin with the same remote URL and version/commit (if specified) will be compared.
#     :type plugin_spec: PluginSpecification
#     :param require_local: Whether to only compare against a registered plugin if it has a local path. Default is True.
#     :type require_local: bool
#     """
#     # Get logger
#     logger = get_logger()

#     # Check source type
#     if Path(plugin_source).is_dir():
#         source_type = PluginSpecificationEnum.LOCAL_PATH
#     elif is_git_repo(plugin_source):
#         source_type = PluginSpecificationEnum.GIT_REMOTE
#     else:
#         logger.error(
#             f"Invalid plugin source '{plugin_source}': Must be either a local "
#             "path or a Git Query whose URL points to an existing repository."
#         )
#         return None

#     # Check that the plugin is registered
#     if not is_plugin_registered(plugin_spec, home_registry=True, package_registry=True, require_local=require_local):
#         logger.debug(
#             f"Plugin '{plugin_spec}' is not registered. Skipping..."
#         )
#         return None

#     # Get the source's version
#     if source_type == PluginSpecificationEnum.LOCAL_PATH:
#         source_version = get_local_plugin_version(plugin_source)
#         if source_version is None:
#             logger.error(
#                 f"Plugin source '{plugin_source}' has an invalid or no version. Skipping..."
#             )
#             return None
#     else:
#         source_version = get_remote_plugin_version(plugin_source)
#         if source_version is None:
#             logger.error(
#                 f"Plugin source '{plugin_source}' has an invalid or no version. Skipping..."
#             )
#             return None

#     # Get the registered version
#     current_version = get_plugin_version(plugin_spec, require_local=require_local)

#     return compare_versions(source_version, current_version)


@typecheck
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
            plugin_spec = load_toml(plugin_path / GURK_METADATA_FILENAME)[
                "project"
            ]["name"]
        except Exception as e:
            logger.error(
                f"Failed to load plugin name from '{plugin_path}': {str(e)}"
            )
            return False

        # Check that there is no plugin with the same name registered with a remote
        if is_plugin_registered(
            plugin_spec,
            home_registry=True,
            package_registry=True,
            require_local=False,
        ):
            registration = get_plugin_registration(
                plugin_spec,
                home_registry=True,
                package_registry=True,
                require_local=False,
            )
            entry = next(iter(registration.values()))
            if entry.get("remote") is not None:
                logger.error(
                    "A plugin with the same name as the specified local plugin already "
                    f"exists with a remote URL registered ({entry['remote']}), so the "
                    "two plugins are considered different. Please change the specification "
                    f"or remove the existing plugin first using 'gurk remove {plugin_spec}'."
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
            logger.success(
                f"Successfully installed plugin from '{plugin_source}'"
            )
        else:
            logger.error(f"Failed to install plugin from '{plugin_source}'")
        return success

    # Act depending on whether the plugin is already installed
    if not is_plugin_installed(extract_url(plugin_spec), require_venv=False):
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
        logger.info(f"Plugin '{plugin_spec}' is not currently installed.")
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
                source_version = get_local_plugin_version(plugin_source)
                installed_version = get_plugin_version(
                    plugin_spec, require_local=True
                )
                if (
                    compare_versions(source_version, installed_version)
                    == Comparison.EQUAL
                ):
                    logger.info(
                        f"Plugin '{plugin_spec}' is already installed and "
                        "matches the specified local source version "
                        f"({source_version}). Skipping installation..."
                    )
                    return True
                else:
                    logger.error(
                        f"Plugin '{plugin_spec}' is already installed (v: {installed_version})"
                        ", but does not match the specified local source version "
                        f"(v: {source_version}). Please explictly specify to reinstall it."
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
            if not is_plugin_installed(plugin_spec, require_venv=False):
                if reinstall:
                    reinstall_required = True
                else:
                    logger.error(
                        f"Plugin '{plugin_spec}' is installed at a different "
                        "version than specified (see full log). Use '--replace' "
                        "to reinstall and use the specified version."
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


@typecheck
def upgrade_plugin(
    plugin_spec: PluginSpecification, require_local: bool = True
) -> bool:
    """
    Upgrade an installed plugin to the latest version available at its registered remote URL.

    :param plugin_spec: Name, PathLike, or GitQuery of the plugin to upgrade. If a GitQuery is provided, it is only used to identify the plugin to upgrade.
    :type plugin_spec: PluginSpecification
    :param require_local: Whether to only consider plugins with a local installation when looking for the plugin to upgrade. When upgrading a remote-only plugin, it is not installed here, but its registry entry is updated to point to the new version.
    :type require_local: bool
    :return: True if the plugin was upgraded successfully, False otherwise
    :rtype: bool
    """
    # Get logger
    logger = get_logger()

    # Check that the plugin is registered
    if not is_plugin_registered(
        plugin_spec,
        home_registry=True,
        package_registry=True,
        require_local=require_local,
    ):
        logger.debug(f"Plugin '{plugin_spec}' is not registered. Skipping...")
        return False

    # Check that the plugin has a registered remote URL
    plugin_remote = next(
        iter(
            get_plugin_registration(
                plugin_spec,
                home_registry=True,
                package_registry=True,
                require_local=require_local,
            ).values()
        )
    )["remote"]
    if plugin_remote is None:
        logger.error(f"Plugin '{plugin_spec}' is local-only. Skipping...")
        return False

    # Get the latest version available at the registered remote URL
    latest_version = get_latest_version(plugin_remote)
    if latest_version is None:
        logger.error(
            f"Failed to get the latest version for plugin '{plugin_spec}' from its registered remote URL. Skipping..."
        )
        return False

    # Get the current registered version (if any)
    current_version = get_plugin_version(
        plugin_spec, require_local=require_local
    )
    if current_version is None:
        logger.error(
            f"Failed to get the registered version for plugin '{plugin_spec}'. Skipping..."
        )
        return False

    # # Check if the registered version is already the latest version
    version_comparison = compare_versions(latest_version, current_version)
    if version_comparison is None:
        logger.error(
            f"Failed to compare versions for plugin '{plugin_spec}'. Skipping..."
        )
        return False
    elif version_comparison == Comparison.EQUAL:
        logger.info(
            f"Plugin '{plugin_spec}' is already at the latest version ({current_version})."
        )
        return True
    elif version_comparison == Comparison.SMALLER:
        logger.warning(
            f"Unexpected: Plugin '{plugin_spec}' version ({current_version}) "
            f"is newer than latest ({latest_version}). Skipping..."
        )
        return False
    else:
        logger.info(
            f"Upgrading plugin '{plugin_spec}' from {current_version} to {latest_version}..."
        )
        # Get the current relevant files
        current_relevant_files = get_relevant_plugin_files(plugin_spec)
        if current_relevant_files is None:
            logger.error(
                f"Failed to get relevant files for plugin '{plugin_spec}'."
            )
            return False
        current_remote = edit_url(
            extract_url(plugin_remote), version=current_version
        )

        # Get the latest relevant files
        latest_relevant_files = get_relevant_plugin_files(plugin_remote)
        if latest_relevant_files is None:
            logger.error(
                f"Failed to pull relevant files for plugin '{plugin_spec}'."
            )
            return False
        latest_remote = edit_url(
            extract_url(plugin_remote), version=latest_version
        )

        # Check if the relevant files have changed
        if current_relevant_files == latest_relevant_files:
            abs_current_relevant_files = get_relevant_plugin_files(
                current_remote, relative=False
            )
            abs_latest_relevant_files = get_relevant_plugin_files(
                latest_remote, relative=False
            )
            if len(abs_current_relevant_files) != len(
                abs_latest_relevant_files
            ):
                files_differ = True
            else:
                files_differ = False
                for cfile, lfile in zip(
                    sorted(current_relevant_files),
                    sorted(latest_relevant_files),
                ):
                    if (
                        cfile.name == GURK_METADATA_FILENAME
                        and lfile.name == GURK_METADATA_FILENAME
                    ):
                        # Skip comparing pyproject.toml, since we already know it has a version change
                        #   Dependency changes are reflected in other changed files
                        continue
                    elif not filecmp.cmp(
                        cfile,
                        lfile,
                        shallow=False,
                    ):
                        files_differ = True
                        break

            if not files_differ:
                logger.info(
                    f"Plugin '{plugin_spec}' files unchanged. Skipping..."
                )
                return True

    # Handle upgrading to the latest version based on if the plugin is installed
    if not is_plugin_installed(extract_url(plugin_spec), require_venv=False):
        # Update registry entry to point to the latest version at the registered remote URL
        if not update_registry(
            plugin_spec,
            {"remote": latest_remote},
        ):
            logger.error(
                f"Failed to update registry entry for plugin '{plugin_spec}' to version {latest_version}."
            )
            return False
    else:
        # Reinstall plugin at the latest version
        if not install_plugin(latest_remote, reinstall=True):
            logger.error(
                f"Failed to upgrade plugin '{plugin_spec}' to version {latest_version}."
            )
            return False

    return True
