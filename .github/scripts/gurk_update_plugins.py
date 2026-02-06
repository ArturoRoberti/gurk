try:
    from gurk.lib.utils.common import check_version
    from gurk.lib.utils.configs import dump_yaml
    from gurk.lib.utils.plugins import (
        _get_plugin_registry_files,
        get_plugin_registries,
    )
    from gurk.lib.utils.remotes import (
        commit2version,
        edit_url,
        get_latest_version,
        parse_git_query,
        version2commit,
    )
except ImportError:
    raise ImportError(
        "The gurk package needs to be installed to run this script."
    )

from packaging.version import Version

if __name__ == "__main__":
    # Load package registry
    registry_file = _get_plugin_registry_files(home_registry=False)[0]
    registry = get_plugin_registries(home_registry=False)[0]

    # Check for new remote plugin versions
    errors_found = False
    for plugin_source, plugin_data in registry.items():
        if not plugin_data.get("remote"):
            continue  # Skip local plugins
        parsed = parse_git_query(plugin_data["remote"])

        # Get current version
        current_version = commit2version(parsed["url"], parsed["commit"])
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
            new_commit = version2commit(parsed["url"], latest_version)
            if not new_commit:
                # This should not happen since we just got the version from the same remote, but check just in case
                print(
                    f"ERROR: Could not determine commit for latest version of {plugin_source}."
                )
                errors_found = True
                continue

            plugin_data["remote"] = edit_url(
                plugin_data["remote"], commit=new_commit
            )

    # If errors found, exit with error
    if errors_found:
        raise SystemExit(1)

    # Save updated registry
    dump_yaml(registry, registry_file)
    print("Plugin registry updated successfully.")
