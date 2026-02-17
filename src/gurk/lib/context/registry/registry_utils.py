from copy import deepcopy
from pathlib import Path
from typing import Literal, TypeVar, get_type_hints, overload

from gurk.lib.shared.plugins import (
    PluginRegistry,
    PluginRegistryEntry,
    ZippedRegistry,
)
from gurk.lib.shared.remotes import GitQueryDict, is_git_repo, parse_git_query
from gurk.lib.utils import (
    PACKAGE_HOME_PATH,
    PACKAGE_SRC_PATH,
    PathLike,
    full_isinstance,
    typecheck,
)

from ..logger import get_logger


@typecheck
def _deepcopy_tuple(tup: tuple) -> tuple:
    """
    Deepcopy a tuple by deepcopying each item and returning a new tuple.

    :param tup: Tuple to deepcopy
    :type tup: tuple
    :return: Deepcopied tuple
    :rtype: tuple
    """
    return tuple(deepcopy(item) for item in tup)


@typecheck
def get_plugin_directories(
    home_registry: bool = True, package_registry: bool = True
) -> tuple[Path, ...]:
    """
    Get a tuple of plugin directories, with the home one first.

    :param home_registry: Whether to include the home plugin directory
    :type home_registry: bool
    :param package_registry: Whether to include the package plugin directory
    :type package_registry: bool
    :return: Tuple of plugin directories (home, package), depending on the input
    :rtype: tuple[Path, ...]
    :raises TypeError: If an expected plugin directory path exists but is not a directory
    """
    parent_paths: list[Path] = []
    if home_registry:
        parent_paths.append(PACKAGE_HOME_PATH)
    if package_registry:
        parent_paths.append(PACKAGE_SRC_PATH)

    possible_plugin_paths = [p / "plugins" for p in parent_paths]
    for p in possible_plugin_paths:
        if p.is_file():
            raise TypeError(
                f"Expected plugin directory at '{p.as_posix()}', but "
                "found a file. Please remove or rename this file."
            )
        p.mkdir(parents=True, exist_ok=True)

    return tuple(possible_plugin_paths)


def _get_registry_files() -> tuple[Path, Path]:
    """
    Get a tuple of plugin registries, with the home one first.

    :return: Tuple of plugin registries (home, package)
    :rtype: tuple[Path, Path]
    """
    plugin_registry_files = [
        p / "registry.yaml" for p in get_plugin_directories()
    ]
    for p in plugin_registry_files:
        p.touch(exist_ok=True)

    return tuple(plugin_registry_files)


def _zip_registry_files(
    registries: tuple[PluginRegistry, PluginRegistry]
) -> tuple[ZippedRegistry, ...]:
    """
    Zip the plugin registries with their corresponding registry files, with the home one first.

    :param registries: Tuple of plugin registries (home, package)
    :type registries: tuple[PluginRegistry, PluginRegistry]
    :return: Tuple of tuples of plugin registry files and their corresponding registries (home, package)
    :rtype: tuple[ZippedRegistry, ...]
    """
    return tuple(zip(_get_registry_files(), registries))


@typecheck
def _expand_registry_path(
    registry_file: PathLike, path: PathLike, collapse: bool = False
) -> Path:
    """
    Expand the "local" path of a plugin registry entry to an absolute path based on the registry file's location.

    :param registry_file: Path to the registry file
    :type registry_file: PathLike
    :param path: Path to expand
    :type path: PathLike
    :param collapse: Whether to collapse the path instead of expanding it
    :type collapse: bool
    :return: Expanded plugin registry entry
    :rtype: Path
    """
    registry_file = Path(registry_file).expanduser()
    if collapse:
        return Path(path).relative_to(registry_file.parent)
    else:
        return (registry_file.parent / path).expanduser().resolve()


@typecheck
def _is_entry_valid(
    name: str,
    entry: PluginRegistryEntry,
    registry_file: Path,
    check_local: bool = True,
) -> bool:
    """
    Check if a plugin registry entry is valid.

    :param name: Name of the plugin
    :param entry: Plugin registry entry to validate
    :param registry_file: Path to the registry file
    :param check_local: Whether to check that the local path exists on disk (if specified).
    :return: Whether the entry is valid
    """
    checks: dict[str, bool] = {
        "Plugin name must be a string": isinstance(name, str),
        "Entry must conform to PluginRegistryEntry schema": full_isinstance(
            entry, PluginRegistryEntry
        ),
        "Entry must define at least one of 'local' or 'remote'": any(
            (entry.get("local") is not None, entry.get("remote") is not None)
        ),
        "Local path must exist if specified": (
            entry.get("local") is None
            or (
                not check_local
                or _expand_registry_path(
                    registry_file, entry["local"]
                ).is_dir()
            )
        ),
        "Remote must be a valid git repository if specified": (
            entry.get("remote") is None or is_git_repo(entry["remote"])
        ),
        "Remote must define a commit (and nothing else) if specified": (
            entry.get("remote") is None
            or (
                parse_git_query(entry["remote"])["commit"] is not None
                and all(
                    parse_git_query(entry["remote"])[f] is None
                    for f in get_type_hints(GitQueryDict)
                    if f not in ("url", "commit")
                )
            )
        ),
    }

    failed_checks = [msg for msg, passed in checks.items() if not passed]

    if failed_checks:
        failed_msgs = "\n- " + "\n- ".join(failed_checks)
        get_logger().debug(
            f"Invalid plugin registry entry '{name}' in "
            f"{registry_file.as_posix()}:{failed_msgs}"
        )
        return False

    return True


T = TypeVar("T")


@overload
def _filter_by_registries(
    tup: tuple[T, T],
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[False] = ...,
    dcopy: bool = ...,
) -> T:
    ...


@overload
def _filter_by_registries(
    tup: tuple[T, T],
    *,
    home_registry: Literal[False] = ...,
    package_registry: Literal[True] = ...,
    dcopy: bool = ...,
) -> T:
    ...


@overload
def _filter_by_registries(
    tup: tuple[T, T],
    *,
    home_registry: Literal[True] = ...,
    package_registry: Literal[True] = ...,
    dcopy: bool = ...,
) -> tuple[T, T]:
    ...


@typecheck
def _filter_by_registries(
    tup: tuple[T, T],
    *,
    home_registry: bool,
    package_registry: bool,
    dcopy: bool = False,
) -> tuple[T, T] | T:
    """
    Filter a tuple by the requested registries.

    :param tup: Tuple to filter
    :type tup: tuple[T, T]
    :param home_registry: Whether to include the home registry
    :type home_registry: bool
    :param package_registry: Whether to include the package registry
    :type package_registry: bool
    :param dcopy: Whether to deepcopy the entries
    :type dcopy: bool
    :return: Filtered tuple or single entry, depending on the input
    :rtype: tuple[T, T] | T
    """
    filtered = []
    if home_registry:
        filtered.append(deepcopy(tup[0]) if dcopy else tup[0])
    if package_registry:
        filtered.append(deepcopy(tup[1]) if dcopy else tup[1])
    return filtered[0] if len(filtered) == 1 else tuple(filtered)
