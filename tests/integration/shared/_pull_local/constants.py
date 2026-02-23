from gurk.lib.shared.remotes import edit_url

from ...utils import EXAMPLE_PLUGIN_VERSIONING, PYTEST_PLUGIN_PATH, bump_patch

existing_version = EXAMPLE_PLUGIN_VERSIONING["version"]["exists"]
LOCAL_PLUGIN_VERSIONS = {
    existing_version,  # Existing version
    bump_patch(existing_version),  # New version
}

VALID_LOCAL_PATH_SPECIFICATION_OPTIONS = {
    str(PYTEST_PLUGIN_PATH)
}  # simple local path
INVALID_LOCAL_PATH_SPECIFICATION_OPTIONS = {
    edit_url(
        str(PYTEST_PLUGIN_PATH), version=existing_version
    ),  # with version
    "non-existent-path",  # non-existent path
}
