from gurk.lib.shared.remotes import edit_url

from ...utils import EXAMPLE_PLUGIN_REMOTE, EXAMPLE_PLUGIN_VERSIONING

# Valid specifications
VALID_GIT_QUERY_SPECIFICATION_OPTIONS = {
    EXAMPLE_PLUGIN_REMOTE
}  # simple remote
VALID_GIT_QUERY_SPECIFICATION_OPTIONS.update(  # existing/valid versioning fields
    {
        edit_url(EXAMPLE_PLUGIN_REMOTE, **{field: existences["exists"]})
        for field, existences in EXAMPLE_PLUGIN_VERSIONING.items()
    }
)

# Invalid specifications
INVALID_GIT_QUERY_SPECIFICATION_OPTIONS = (
    {  # missing/invalid versioning fields
        edit_url(EXAMPLE_PLUGIN_REMOTE, **{field: existences["missing"]})
        for field, existences in EXAMPLE_PLUGIN_VERSIONING.items()
    }
)
INVALID_GIT_QUERY_SPECIFICATION_OPTIONS.add(  # multiple versioning fields
    edit_url(
        EXAMPLE_PLUGIN_REMOTE,
        **{
            field: existences["exists"]
            for field, existences in EXAMPLE_PLUGIN_VERSIONING.items()
        },
    )
)
