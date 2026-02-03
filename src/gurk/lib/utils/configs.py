from copy import deepcopy
from pathlib import Path
from typing import Any

import tomli_w
import tomllib
from ruamel.yaml import YAML as RuamelYAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from gurk.lib.utils.common import PathLike, resolve_package_path

YAML = RuamelYAML()
YAML.preserve_quotes = True
YAML.indent(mapping=2, sequence=2, offset=0)
YAML.Representer.add_representer(
    type(None),
    lambda self, data: self.represent_scalar("tag:yaml.org,2002:null", "null"),
)  # conserve 'null'


def load_toml(toml_file: PathLike) -> dict[str, Any] | None:
    """
    Load a TOML file.

    :param toml_file: Path to the TOML file to load
    :type toml_file: PathLike
    :return: Content of the TOML file, or None if loading fails
    :rtype: dict[str, Any] | None
    """
    if not Path(toml_file).is_file():
        return None

    with open(toml_file, "rb") as f:
        try:
            return tomllib.load(f) or {}
        except tomllib.TOMLDecodeError:
            return None


def dump_toml(toml_file: PathLike, content: dict[str, Any]) -> None:
    """
    Dump content to a TOML file.

    :param toml_file: Path to the TOML file to dump to
    :type toml_file: PathLike
    :param content: Content to dump
    :type content: dict[str, Any]
    """
    with open(toml_file, "wb") as f:
        tomli_w.dump(content, f)


def load_yaml(
    yaml_file: PathLike, remove_list_duplicates: bool = True
) -> dict[str, Any] | None:
    """
    Load a YAML file and normalize its content.

    :param yaml_file: Path to the YAML file to load
    :type yaml_file: PathLike
    :param remove_list_duplicates: Whether to remove duplicates in lists
    :type remove_list_duplicates: bool
    :return: Normalized content of the YAML file, or None if loading fails
    :rtype: dict[str, Any] | None
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

    if not Path(yaml_file).is_file():
        return None

    with open(yaml_file, "r") as f:
        try:
            content = YAML.load(f) or {}
        except Exception:
            return None
    return normalize_yaml(content)


def dump_yaml(content: dict[str, Any], yaml_file: PathLike) -> None:
    """
    Dump content to a YAML file.

    :param content: Content to dump
    :type content: dict[str, Any]
    :param yaml_file: Path to the YAML file to dump to
    :type yaml_file: PathLike
    """
    with open(yaml_file, "w", encoding="utf-8") as f:
        YAML.dump(content, f)


def overlay_dicts(dicts: list[dict]) -> dict:
    """
    Overlay multiple dictionaries in order, with later
    dictionaries replacing or updating keys in earlier ones.

    :param dicts: List of dictionaries to overlay
    :type dicts: list[dict]
    :return: The resulting overlaid dictionary
    :rtype: dict
    :raises ValueError: If any item in dicts is not a dictionary
    """

    def _overlay_two_dicts(base: dict, overlay: dict) -> dict:
        """
        Recursively overlay overlay-dict onto base-dict.
        Keys in overlay replace or update those in base.

        :param base: The base dictionary to overlay onto
        :type base: dict
        :param overlay: The overlay dictionary with updates
        :type overlay: dict
        :return: The resulting dictionary after overlay
        :rtype: dict
        """
        overlayed = deepcopy(base)
        for key, value in overlay.items():
            if (
                key in overlayed
                and isinstance(overlayed[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively overlay nested dicts
                overlayed[key] = _overlay_two_dicts(overlayed[key], value)
            else:
                # Directly set/replace value
                overlayed[key] = value
        return overlayed

    # Check input
    if not all(isinstance(d, dict) for d in dicts):
        raise ValueError(
            "Input 'dicts' must be a list of dictionaries, "
            f"got: {[type(d) for d in dicts]}"
        )

    # Overlay all dictionaries in order
    overlayed_dict = deepcopy(dicts[0])
    for current_dict in dicts[1:]:
        overlayed_dict = _overlay_two_dicts(overlayed_dict, current_dict)

    return overlayed_dict
