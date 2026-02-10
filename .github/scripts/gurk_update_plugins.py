try:
    from gurk.lib.core.context import (
        GurkContext,
        get_registries,
        update_registry,
    )
    from gurk.lib.utils.common import check_version
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

# TODO: Only upgrade if relevant files have changed (except for pyproject.toml)

from packaging.version import Version

if __name__ == "__main__":
    with GurkContext(logger=None, writable=True):
        # Check for new remote plugin versions
        errors_found = False
        for plugin_name, entry in get_registries(
            home_registry=False, package_registry=True
        ).items():
            if not entry.get("remote"):
                continue  # Skip local plugins
            parsed = parse_git_query(entry["remote"])

            # Get current version
            current_version = commit2version(parsed["url"], parsed["commit"])
            if not current_version or not check_version(current_version):
                print(
                    f"ERROR: Plugin {plugin_name} does not have a valid version specified."
                )
                errors_found = True
                continue

            # Get latest version
            latest_version = get_latest_version(parsed["url"])
            if not latest_version or not check_version(latest_version):
                print(
                    f"ERROR: Could not determine valid latest version for {plugin_name}."
                )
                errors_found = True
                continue

            # Update version if necessary
            if Version(current_version) < Version(latest_version):
                new_commit = version2commit(parsed["url"], latest_version)
                if not new_commit:
                    # This should not happen since we just got the version from the same remote, but check just in case
                    print(
                        f"ERROR: Could not determine commit for latest version of {plugin_name}."
                    )
                    errors_found = True
                    continue
                update_registry(
                    plugin_name,
                    {"remote": edit_url(entry["remote"], commit=new_commit)},
                    package_registry=True,
                )

        # If errors found, exit with error
        if errors_found:
            raise SystemExit(1)
        else:
            # Register updates registry upon exit
            print("Plugin registry updated successfully.")
