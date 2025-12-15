from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML

from cmstp.utils.common import resolve_package_path


def load_yaml(yaml_file: Path) -> Optional[Dict[str, Any]]:
    """
    Load a YAML file and normalize its content.

    :param yaml_file: Path to the YAML file to load
    :type yaml_file: Path
    :return: Normalized content of the YAML file, or None if loading fails
    :rtype: Dict[str, Any] | None
    """

    def join_constructor(loader, node):
        """Custom !join constructor to concatenate strings and aliases."""
        parts = loader.construct_sequence(node)
        return "".join(parts)

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

    if not yaml_file.exists():
        return None

    yaml = YAML(typ="safe")
    yaml.constructor.add_constructor("!join", join_constructor)
    with open(yaml_file, "r") as f:
        try:
            content = yaml.load(f) or {}
        except Exception:
            return None
    return normalize_yaml(content)


def overlay_dicts(dicts: List[Dict], allow_default: bool = False) -> Dict:
    """
    Overlay multiple dictionaries in order, with later dictionaries
    replacing or updating keys in earlier ones. If allow_default is True,
    keys with the value "default" in overlaying dictionaries will keep
    the value from the base dictionary.

    :param dicts: List of dictionaries to overlay
    :type dicts: List[Dict]
    :param allow_default: Whether to allow "default" values to keep base values
    :type allow_default: bool
    :return: The resulting overlaid dictionary
    :rtype: Dict
    """

    def _overlay_two_dicts(
        base: Dict, overlay: Dict, allow_default: bool = False
    ) -> Dict:
        """
        Recursively overlay overlay-dict onto base-dict.
        Keys in overlay replace or update those in base, unless the value is "default".

        :param base: The base dictionary to overlay onto
        :type base: Dict
        :param overlay: The overlay dictionary with updates
        :type overlay: Dict
        :param allow_default: Whether to allow "default" values to keep base values
        :type allow_default: bool
        :return: The resulting dictionary after overlay
        :rtype: Dict
        """
        overlayed = deepcopy(base)
        for key, value in overlay.items():
            if allow_default and key in overlayed and value == "default":
                # Keep base value
                continue
            elif (
                key in overlayed
                and isinstance(overlayed[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively overlay nested dicts
                overlayed[key] = _overlay_two_dicts(
                    overlayed[key], value, allow_default
                )
            else:
                # Directly set/replace value
                overlayed[key] = value
        return overlayed

    # Check input
    if not all(isinstance(d, dict) for d in dicts):
        raise ValueError("Input 'dicts' must be a list of dictionaries.")

    # Overlay all dictionaries in order
    overlayed_dict = deepcopy(dicts[0])
    for current_dict in dicts[1:]:
        overlayed_dict = _overlay_two_dicts(
            overlayed_dict, current_dict, allow_default
        )

    return overlayed_dict
