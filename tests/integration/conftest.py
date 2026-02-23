from copy import deepcopy
from typing import Iterator

import pytest

from .shared import (
    INVALID_GIT_QUERY_SPECIFICATION_OPTIONS,
    INVALID_LOCAL_PATH_SPECIFICATION_OPTIONS,
    INVALID_NAME_SPECIFICATION_OPTIONS,
    LOCAL_PLUGIN_VERSIONS,
    PREPARED_PLUGIN_REGISTRATION_PARAMS,
    VALID_GIT_QUERY_SPECIFICATION_OPTIONS,
    VALID_LOCAL_PATH_SPECIFICATION_OPTIONS,
    VALID_NAME_SPECIFICATION_OPTIONS,
    PreparedLocalPlugin,
    PreparedPluginRegistration,
    prepared_plugin_registration_id,
)


################################################################################################
##################################### Prepared Registration ####################################
################################################################################################
@pytest.fixture(
    params=PREPARED_PLUGIN_REGISTRATION_PARAMS,
    ids=lambda p: prepared_plugin_registration_id(p),
)
def prepared_plugin_registration(
    request: pytest.FixtureRequest,
) -> Iterator[PreparedPluginRegistration]:
    """Fixture to set up plugin registrations in various configurations for testing."""
    entry, kind, venv_exists = deepcopy(request.param)
    # Yield a context manager that sets up the plugin registration as specified
    with PreparedPluginRegistration(
        entry=entry,
        kind=kind,
        venv_exists=venv_exists,
    ) as registration:
        yield registration


@pytest.fixture()
def missing_plugin_registration() -> Iterator[PreparedPluginRegistration]:
    """Fixture to set up missing plugin registrations in various configurations for testing."""
    with PreparedPluginRegistration(entry=None) as registration:
        yield registration


################################################################################################
####################################### Pull Local Plugin ######################################
################################################################################################
@pytest.fixture(params=LOCAL_PLUGIN_VERSIONS)
def local_plugin_path(request: pytest.FixtureRequest) -> Iterator[str]:
    """Fixture to set up a local plugin path for testing."""
    with PreparedLocalPlugin(version=request.param) as plugin:
        yield plugin


@pytest.fixture(params=VALID_LOCAL_PATH_SPECIFICATION_OPTIONS)
def valid_local_plugin_specification(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Fixture to set up valid local plugin specifications for testing."""
    yield request.param


@pytest.fixture(params=INVALID_LOCAL_PATH_SPECIFICATION_OPTIONS)
def invalid_local_plugin_specification(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Fixture to set up invalid local plugin specifications for testing."""
    yield request.param


################################################################################################
###################################### Pull Remote Plugin ######################################
################################################################################################
@pytest.fixture(params=VALID_GIT_QUERY_SPECIFICATION_OPTIONS)
def valid_remote_plugin_specification(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Fixture to set up a remote plugin with various versions for testing."""
    yield request.param


@pytest.fixture(params=INVALID_GIT_QUERY_SPECIFICATION_OPTIONS)
def invalid_remote_plugin_specification(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Fixture to set up invalid remote plugin specifications for testing."""
    yield request.param


################################################################################################
######################################### Remove Plugin ########################################
################################################################################################
@pytest.fixture(params=VALID_NAME_SPECIFICATION_OPTIONS)
def valid_plugin_name_specification(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Fixture to set up a valid plugin name for testing removal."""
    yield request.param


@pytest.fixture(params=INVALID_NAME_SPECIFICATION_OPTIONS)
def invalid_plugin_name_specification(
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Fixture to set up an invalid plugin name for testing removal."""
    yield request.param
