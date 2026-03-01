from importlib.util import find_spec
from pathlib import Path

TEMPLATE_PLUGIN_NAME = "gurk-template-plugin"
try:
    spec = find_spec(TEMPLATE_PLUGIN_NAME.replace("-", "_"))
    TEMPLATE_PLUGIN_PATH = Path(spec.submodule_search_locations[0])
except Exception:
    TEMPLATE_PLUGIN_PATH = None
