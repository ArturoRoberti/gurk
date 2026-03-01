import shutil
from dataclasses import dataclass, field

from packaging.version import InvalidVersion, Version

from gurk.lib.shared.configs import dump_toml, load_toml
from gurk.lib.utils import GURK_METADATA_FILENAME

from ...utils import (
    PYTEST_PLUGIN_NAME,
    PYTEST_PLUGIN_PATH,
    TEMPLATE_PLUGIN_VERSIONING,
    PytestInputException,
    PytestUnexpectedException,
)
from .cli import gurk_template


@dataclass
class PreparedLocalPlugin:
    """
    Context manager to create and clean up a template local plugin for testing.

    :param version: The version string to set in the plugin metadata. Must be a valid version string parsable by `packaging.version.Version`.
    :type version: str
    """

    # fmt: off
    version:   str  = field(default=TEMPLATE_PLUGIN_VERSIONING["version"]["exists"])
    # fmt: on

    def __post_init__(self):
        # Validate version string
        try:
            Version(self.version)
        except InvalidVersion:
            raise PytestInputException(
                f"Invalid version string '{self.version}' provided for the template plugin context."
            )

    def __enter__(self) -> str:
        # Create a local plugin to pull from
        gurk_template(
            [
                f"--name={PYTEST_PLUGIN_NAME}",
                f"--directory={PYTEST_PLUGIN_PATH.parent.as_posix()}",
            ]
        )
        if not PYTEST_PLUGIN_PATH.is_dir():
            raise PytestUnexpectedException(
                f"Expected a directory for the plugin, but it was not found at {PYTEST_PLUGIN_PATH}"
            )

        # Edit the plugin metadata as requested
        ## Load metadata
        metadata_file = PYTEST_PLUGIN_PATH / GURK_METADATA_FILENAME
        metadata = load_toml(metadata_file)
        if metadata["project"]["name"] != PYTEST_PLUGIN_NAME:
            raise PytestUnexpectedException(
                f"Expected plugin name in metadata to be '{PYTEST_PLUGIN_NAME}', but found '{metadata['project']['name']}'"
            )
        ## Set the version field to the specified version
        metadata["project"]["version"] = self.version
        ## Dump the modified metadata back to the file
        dump_toml(metadata, metadata_file)

        return PYTEST_PLUGIN_PATH.as_posix()

    def __exit__(self, exc_type, exc, tb):
        # Remove the local plugin created for testing
        if PYTEST_PLUGIN_PATH.is_dir():
            shutil.rmtree(PYTEST_PLUGIN_PATH)
        elif PYTEST_PLUGIN_PATH.is_file():
            raise PytestUnexpectedException(
                f"Expected a directory for the plugin, but found a file at {PYTEST_PLUGIN_PATH}"
            )
        return False  # Don't suppress exceptions
