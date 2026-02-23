from pathlib import Path

from gurk.lib.context import get_logger, get_plugin_registration
from gurk.lib.shared.configs import load_toml
from gurk.lib.shared.plugins import PluginSpecification
from gurk.lib.shared.remotes import (
    GitQuery,
    commit2version,
    determine_ref,
    get_commit,
    parse_git_query,
)
from gurk.lib.utils import (
    GURK_METADATA_FILENAME,
    PathLike,
    check_version,
    typecheck,
)


@typecheck
def get_local_plugin_version(plugin_path: PathLike) -> str | None:
    """
    Return the version string from the pyproject.toml file in a local repository path, or None if not found.
        :NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param plugin_path: Path to the local repository
    :type plugin_path: PathLike
    :return: Version string, or None if not found
    :rtype: str | None
    """
    try:
        version = load_toml(Path(plugin_path) / GURK_METADATA_FILENAME)[
            "project"
        ]["version"]
        if not check_version(version):
            raise ValueError
        return version
    except Exception:
        return None


@typecheck
def get_remote_plugin_version(remote: GitQuery) -> str | None:
    """
    Return the version string of a repository remote, or None if not found.

    :param remote: GitQuery of the remote
    :type remote: GitQuery
    :return: Version string, or None if not found
    :rtype: str | None
    """
    parsed = parse_git_query(remote)
    commit = determine_ref(remote, to_commit=True)
    if not commit:
        return None

    version = commit2version(parsed["url"], commit)
    if not check_version(version):
        return None

    return version


@typecheck
def get_plugin_version(
    plugin_spec: PluginSpecification, require_local: bool = False
) -> str | None:
    """
    Return the version of a registered plugin, or None if not found.

    :param plugin_spec: Name, PathLike, or GitQuery of the plugin
    :type plugin_spec: PluginSpecification
    :param require_local: If True, only return version if plugin has a local path. Otherwise, also check remote URL. Default is False.
    :type require_local: bool
    :return: Version string, or None if not found
    :rtype: str | None
    """
    # Get logger
    logger = get_logger()

    def warning(msg: str) -> None:
        logger.warning(
            f"Registration of plugin '{plugin_spec}' has a {msg}. Please reinstall this plugin."
        )

    # Get registration
    plugin_registration = get_plugin_registration(
        plugin_spec,
        home_registry=True,
        package_registry=True,
        require_local=require_local,
    )
    if not plugin_registration:
        return None
    plugin_registration_entry = next(iter(plugin_registration.values()))

    # Determine local and remote versions
    local = plugin_registration_entry["local"]
    local_version = None
    remote = plugin_registration_entry["remote"]
    remote_version = None
    if local is not None:
        local_version = get_local_plugin_version(local)
        if local_version is None:
            warning("local path with an invalid or no version")
    elif plugin_registration_entry["remote"] is not None:
        remote_version = get_remote_plugin_version(remote)
        if remote_version is None:
            warning("remote URL with an invalid or no version")
    else:
        raise ValueError(
            f"Unexpected: Plugin '{plugin_spec}' is registered "
            "but has no local path or remote URL. "
        )

    if (
        local_version is not None
        and remote_version is not None
        and local_version != remote_version
    ):
        warning(
            f"local version '{local_version}' that does not "
            f"match its remote version '{remote_version}'"
        )
        return None

    return local_version or remote_version


@typecheck
def get_plugin_commit(plugin_spec: PluginSpecification) -> str | None:
    """
    Return the current git commit hash of a local plugin.

    :param plugin_spec: Plugin specification
    :type plugin_spec: PluginSpecification
    :return: Commit hash string, or None if not found
    :rtype: str | None
    """
    # Get plugin registration
    plugin_registration = get_plugin_registration(
        plugin_spec,
        home_registry=True,
        package_registry=True,
        require_local=False,
    )
    if not plugin_registration:
        return None
    plugin_registration_entry = next(iter(plugin_registration.values()))

    parsed = parse_git_query(plugin_registration_entry["remote"])
    return get_commit(parsed["url"], parsed["commit"])
