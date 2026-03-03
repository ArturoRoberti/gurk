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

from .common import PACKAGE_CACHE_PATH

GIT_MIRRORS_DIR = PACKAGE_CACHE_PATH / "git_mirrors"
GIT_MIRRORS_DIR.mkdir(parents=True, exist_ok=True)

PACKAGE_GIT_CACHE_METADATA_PATH = GIT_MIRRORS_DIR / "registry.yaml"
PACKAGE_GIT_CACHE_METADATA_PATH.touch(exist_ok=True)

GIT_QUERY_VERSIONING_FIELDS = {"branch", "commit", "version"}
