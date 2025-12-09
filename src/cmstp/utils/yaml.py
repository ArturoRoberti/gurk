from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from ruamel.yaml import YAML

from cmstp.utils.common import resolve_package_path


def load_yaml(yaml_file: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file and normalize its content."""

    def join_constructor(loader, node):
        """Custom !join constructor to concatenate strings and aliases."""
        parts = loader.construct_sequence(node)
        return "".join(parts)

    def normalize_yaml(obj):
        """
        Recursively normalize YAML content:
        - Convert all numbers to float
        - Remove duplicates in lists
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


def overlay_dicts(
    base: Dict, overlay: Dict, allow_default: bool = False
) -> Dict:
    """
    Recursively overlay overlay-dict onto base-dict.
    Keys in overlay replace or update those in base, unless the value is "default".
    """
    overlayed_dict = deepcopy(base)
    for key, value in overlay.items():
        if allow_default and key in overlayed_dict and value == "default":
            # Keep base value
            continue
        elif (
            key in overlayed_dict
            and isinstance(overlayed_dict[key], dict)
            and isinstance(value, dict)
        ):
            # Recursively overlay nested dicts
            overlayed_dict[key] = overlay_dicts(
                overlayed_dict[key], value, allow_default
            )
        else:
            # Directly set/replace value
            overlayed_dict[key] = value
    return overlayed_dict
