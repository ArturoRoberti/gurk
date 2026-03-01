from gurk.lib.shared.remotes import edit_url

from ...utils import PYTEST_PLUGIN_PATH, TEMPLATE_PLUGIN_VERSIONING, bump_patch

existing_version = TEMPLATE_PLUGIN_VERSIONING["version"]["exists"]
LOCAL_PLUGIN_VERSIONS = {  # TODO: Move to preparation
    existing_version,  # Existing version
    bump_patch(existing_version),  # New version
}

VALID_LOCAL_PATH_SPECIFICATION_OPTIONS = {
    str(PYTEST_PLUGIN_PATH)
}  # simple local path
INVALID_LOCAL_PATH_SPECIFICATION_OPTIONS = {
    edit_url(
        str(PYTEST_PLUGIN_PATH),
        version=TEMPLATE_PLUGIN_VERSIONING["version"]["exists"],
    ),  # with version
    "non-existent-path",  # non-existent path
}
