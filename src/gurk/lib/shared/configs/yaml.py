import os
import re
from importlib import resources
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from gurk.lib.utils import PathLike, PatternCollection, typecheck

from .types import YAML, CommentedDict


@typecheck
def resolve_package_path(raw_script: PathLike, /) -> PathLike | None:
    """
    Resolve paths that may refer to package resources. Package paths are in the format:
    ```
    package://<package-name>/relative/path/inside/package
    ```
    The `package://` pattern does not need to be at the start of the string, and can appear
    multiple times in the string, but only the first occurrence of it is replaced.

    :param raw_script: Raw script path
    :type raw_script: PathLike
    :return: Resolved script path or None if package not found. The output type matches the input type.
    :rtype: PathLike | None
    """
    # Return wrong types as-is
    if not isinstance(raw_script, (Path, str)):
        return raw_script

    raw_str = str(raw_script)

    def _replace_package(match: re.Match) -> str:
        pkg_name, rel_path = match.groups()
        try:
            pkg_root = Path(resources.files(pkg_name))
        except ModuleNotFoundError:
            raise

        return str(pkg_root / rel_path)

    try:
        # Replace ALL occurrences of package://... anywhere in the string
        resolved_str = PatternCollection.PATH.patterns["package"].sub(
            _replace_package, raw_str
        )
    except ModuleNotFoundError:
        return None

    # NOTE: We use 'os' and no built-in 'Path' method to retain consecutive slashes
    resolved_str = os.path.expanduser(resolved_str)

    # Return same type as input
    if isinstance(raw_script, Path):
        return Path(resolved_str)
    else:
        return resolved_str


@typecheck
def load_yaml(
    yaml_file_or_str: PathLike,
    /,
    *,
    from_str: bool = False,
    remove_list_duplicates: bool = True,
) -> Any | None:
    """
    Load a YAML content and normalize it.

    :param yaml_file_or_str: Path to the YAML file to load or a string containing YAML content (if 'from_str' is True)
    :type yaml_file_or_str: PathLike
    :param from_str: Whether 'yaml_file_or_str' is a string containing YAML content (True) or a file path (False, default)
    :type from_str: bool
    :param remove_list_duplicates: Whether to remove duplicates in lists
    :type remove_list_duplicates: bool
    :return: Normalized content of the YAML file, or None if loading fails
    :rtype: Any | None
    """

    def normalize_yaml(obj: Any) -> Any:
        """
        Recursively normalize YAML content:
        - Convert all numbers to float
        - Remove duplicates in lists (if specified)
        - Resolve package paths in strings
        - Preserve comments and formatting using ruamel.yaml

        :param obj: The object to normalize
        :type obj: Any
        :return: Normalized object
        :rtype: Any
        """
        if not obj:
            # Empty or None
            return obj

        if isinstance(obj, CommentedMap):
            # Normalize values in-place to preserve comments
            for k, v in list(obj.items()):
                obj[k] = normalize_yaml(v)
            return obj

        elif isinstance(obj, CommentedSeq):
            if remove_list_duplicates:
                # Remove duplicates while preserving the original list
                seen = []
                indices_to_remove = []
                for i, item in enumerate(obj):
                    if item in seen:
                        indices_to_remove.append(i)
                    else:
                        seen.append(item)

                # Remove duplicates in reverse order to maintain indices
                for i in reversed(indices_to_remove):
                    del obj[i]

            # Normalize items in-place
            for i, item in enumerate(obj):
                obj[i] = normalize_yaml(item)
            return obj

        elif isinstance(obj, str):
            # Resolve package paths
            return resolve_package_path(obj)

        elif isinstance(obj, bool):
            # Keep booleans as-is
            return obj

        # ATTENTION: bool would evaluate as int here
        elif isinstance(obj, (int, float)):
            # Convert all numbers to float
            return float(obj)

        else:
            # Should not happen
            pass

    if from_str:
        try:
            content = YAML.load(yaml_file_or_str) or {}
        except Exception:
            return None
    else:
        if not Path(yaml_file_or_str).is_file():
            return None
        with open(yaml_file_or_str, "r") as f:
            try:
                content = YAML.load(f) or {}
            except Exception:
                return None
    return normalize_yaml(content)


@typecheck
def dump_yaml(content: CommentedDict[str, Any], yaml_file: PathLike) -> None:
    """
    Dump content to a YAML file.

    :param content: Content to dump
    :type content: CommentedDict[str, Any]
    :param yaml_file: Path to the YAML file to dump to
    :type yaml_file: PathLike
    """
    with open(yaml_file, "w", encoding="utf-8") as f:
        YAML.dump(content, f)
