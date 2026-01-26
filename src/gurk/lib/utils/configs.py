from copy import deepcopy
from pathlib import Path
from typing import Any

import tomllib
from ruamel.yaml import YAML

from gurk.lib.utils.common import resolve_package_path


def load_toml(toml_file: Path) -> dict[str, Any] | None:
    """
    Load a TOML file.

    :param toml_file: Path to the TOML file to load
    :type toml_file: Path
    :return: Content of the TOML file, or None if loading fails
    :rtype: dict[str, Any] | None
    """
    if not toml_file.is_file():
        return None

    with open(toml_file, "rb") as f:
        try:
            return tomllib.load(f) or {}
        except tomllib.TOMLDecodeError:
            return None


def load_yaml(yaml_file: Path) -> dict[str, Any] | None:
    """
    Load a YAML file and normalize its content.

    :param yaml_file: Path to the YAML file to load
    :type yaml_file: Path
    :return: Normalized content of the YAML file, or None if loading fails
    :rtype: dict[str, Any] | None
    """

    def normalize_yaml(obj: Any) -> Any:
        """
        Recursively normalize YAML content:
        - Convert all numbers to float
        - Remove duplicates in lists
        - Resolve package paths in strings

        :param obj: The object to normalize
        :type obj: Any
        :return: Normalized object
        :rtype: Any
        """
        if not obj:
            # Empty or None
            return obj

        if isinstance(obj, dict):
            # Recurse
            return {k: normalize_yaml(v) for k, v in obj.items()}

        elif isinstance(obj, list):
            # Remove duplicates
            unique_list = []
            for item in obj:
                if item not in unique_list:
                    unique_list.append(item)

            # Normalize items (float/int)
            return [normalize_yaml(item) for item in unique_list]

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

    if not yaml_file.is_file():
        return None

    yaml = YAML(typ="safe")
    with open(yaml_file, "r") as f:
        try:
            content = yaml.load(f) or {}
        except Exception:
            return None
    return normalize_yaml(content)


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
