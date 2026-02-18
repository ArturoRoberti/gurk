import sys
from datetime import datetime
from importlib import resources
from importlib.metadata import version
from pathlib import Path

PACKAGE_NAME = "gurk"
GURK_VERSION = version(PACKAGE_NAME)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
PACKAGE_SRC_PATH = Path(resources.files(PACKAGE_NAME)).expanduser().resolve()
PACKAGE_TESTS_PATH = PACKAGE_SRC_PATH.parents[1] / "tests"
PIPX_PYTHON_PATH = Path(sys.executable)

PACKAGE_CACHE_PATH = Path.home() / ".cache" / PACKAGE_NAME
PACKAGE_CACHE_PATH.mkdir(parents=True, exist_ok=True)
