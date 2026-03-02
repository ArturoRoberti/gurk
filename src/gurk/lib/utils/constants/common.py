# Copyright 2026 Arturo Roberti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import sys
from importlib import resources
from importlib.metadata import distribution, version
from pathlib import Path

PACKAGE_NAME = "gurk"
GURK_VERSION = version(PACKAGE_NAME)
PACKAGE_SRC_PATH = Path(resources.files(PACKAGE_NAME)).expanduser().resolve()
PIPX_PYTHON_PATH = Path(sys.executable)
EDITABLE_INSTALL = (
    json.loads(distribution(PACKAGE_NAME).read_text("direct_url.json"))
    .get("dir_info", {})
    .get("editable", False)
)

PACKAGE_CACHE_PATH = Path.home() / ".cache" / PACKAGE_NAME
PACKAGE_CACHE_PATH.mkdir(parents=True, exist_ok=True)
