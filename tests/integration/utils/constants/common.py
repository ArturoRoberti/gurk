from pathlib import Path
from tempfile import TemporaryDirectory

from gurk.lib.utils import TEMPLATE_PLUGIN_NAME

# NOTE: Name needs to be the same as the remote used in testing
PYTEST_PLUGIN_NAME = TEMPLATE_PLUGIN_NAME
with TemporaryDirectory(delete=False) as tmp:
    PYTEST_PLUGIN_PATH = Path(tmp) / PYTEST_PLUGIN_NAME
