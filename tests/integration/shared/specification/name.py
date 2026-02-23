from gurk.lib.shared.remotes import edit_url

from ...utils import EXAMPLE_PLUGIN_VERSIONING, PYTEST_PLUGIN_NAME

VALID_NAME_SPECIFICATION_OPTIONS = {PYTEST_PLUGIN_NAME}  # simple plugin name
INVALID_NAME_SPECIFICATION_OPTIONS = {
    edit_url(
        PYTEST_PLUGIN_NAME,
        version=EXAMPLE_PLUGIN_VERSIONING["version"]["exists"],
    ),  # with version
    "non-existent-name",  # non-existent name
}
