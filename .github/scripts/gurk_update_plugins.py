try:
    from gurk.lib.utils.common import PACKAGE_SRC_PATH, check_version
    from gurk.lib.utils.remotes import (
        edit_url,
        get_latest_version,
        parse_git_ref,
    )
except ImportError:
    raise ImportError(
        "The gurk package needs to be installed to run this script."
    )

from packaging.version import Version
from ruamel.yaml import YAML

if __name__ == "__main__":
    # Setup YAML handler
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=0)
    yaml.Representer.add_representer(
        type(None),
        lambda self, data: self.represent_scalar(
            "tag:yaml.org,2002:null", "null"
        ),
    )  # conserve 'null'

    # Load package registry
    registry_path = PACKAGE_SRC_PATH / "plugins" / "registry.yaml"
    with registry_path.open("r", encoding="utf-8") as f:
        registry = yaml.load(f)

    # Check for new remote plugin versions
    errors_found = False
    for plugin_source, plugin_data in registry.items():
        if not plugin_data.get("remote"):
            continue  # Skip local plugins
        parsed = parse_git_ref(plugin_data["remote"])

        # Get current version
        current_version = parsed["version"]
        if not current_version or not check_version(current_version):
            print(
                f"ERROR: Plugin {plugin_source} does not have a valid version specified."
            )
            errors_found = True
            continue

        # Get latest version
        latest_version = get_latest_version(parsed["url"])
        if not latest_version or not check_version(latest_version):
            print(
                f"ERROR: Could not determine valid latest version for {plugin_source}."
            )
            errors_found = True
            continue

        # Update version if necessary
        if Version(current_version) < Version(latest_version):
            plugin_data["remote"] = edit_url(
                plugin_data["remote"], version=latest_version
            )

    # If errors found, exit with error
    if errors_found:
        raise SystemExit(1)

    # Save updated registry
    with registry_path.open("w", encoding="utf-8") as f:
        yaml.dump(registry, f)

    print("Plugin registry updated successfully.")
