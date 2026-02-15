from pathlib import Path

from gurk.lib.core.context.registry_manager import get_plugin_registration
from gurk.lib.utils.common import PathLike, check_version, typecheck
from gurk.lib.utils.configs import load_toml
from gurk.lib.utils.remotes import get_commit, parse_git_query

from .common import PluginSpecification


@typecheck
def get_local_plugin_version(plugin_path: PathLike) -> str | None:
    """
    Return the version string from the pyproject.toml file in a local repository path, or None if not found.
        NOTE: Assumes version is specified as `version = "<version>"` in pyproject.toml under the [project] section

    :param plugin_path: Path to the local repository
    :type plugin_path: PathLike
    :return: Version string, or None if not found
    :rtype: str | None
    """
    try:
        version = load_toml(Path(plugin_path) / "pyproject.toml")["project"][
            "version"
        ]
        if not check_version(version):
            raise ValueError
        return version
    except Exception:
        return None


@typecheck
def get_plugin_version(plugin: PluginSpecification) -> str | None:
    """
    Return the version string of a local plugin, or None if not found.

    :param plugin: Name, PathLike, or GitQuery of the plugin
    :type plugin: PluginSpecification
    :return: Version string, or None if not found
    :rtype: str | None
    """
    plugin_registration = get_plugin_registration(
        plugin, home_registry=True, package_registry=True
    )
    if not plugin_registration:
        return None
    plugin_registration_entry = next(iter(plugin_registration.values()))

    local_path = plugin_registration_entry["local"]
    return (
        get_local_plugin_version(local_path)
        if local_path is not None
        else None
    )


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
