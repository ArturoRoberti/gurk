from typing import TypedDict, get_type_hints

from gurk.lib.utils import GIT_QUERY_VERSIONING_FIELDS

from .exceptions import PytestUnexpectedException


class VersioningExistence(TypedDict):
    # fmt: off
    exists:  str
    missing: str
    # fmt: on


class PluginVersioning(TypedDict):
    version: VersioningExistence
    branch: VersioningExistence
    commit: VersioningExistence


# Check that all versioning fields have the required exist/missing structure
for field in GIT_QUERY_VERSIONING_FIELDS:
    if field not in get_type_hints(PluginVersioning).keys():
        raise PytestUnexpectedException(
            f"Versioning field '{field}' is missing from the 'PluginVersioning' "
            f"TypedDict - please add it to the class definition in {__file__}."
        )
