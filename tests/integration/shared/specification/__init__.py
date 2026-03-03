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

from .git_query import (
    INVALID_GIT_QUERY_SPECIFICATION_OPTIONS,
    VALID_GIT_QUERY_SPECIFICATION_OPTIONS,
)
from .local_path import (
    INVALID_LOCAL_PATH_SPECIFICATION_OPTIONS,
    VALID_LOCAL_PATH_SPECIFICATION_OPTIONS,
)
from .name import (
    INVALID_NAME_SPECIFICATION_OPTIONS,
    VALID_NAME_SPECIFICATION_OPTIONS,
)

__all__ = [
    "INVALID_GIT_QUERY_SPECIFICATION_OPTIONS",
    "INVALID_LOCAL_PATH_SPECIFICATION_OPTIONS",
    "INVALID_NAME_SPECIFICATION_OPTIONS",
    "VALID_GIT_QUERY_SPECIFICATION_OPTIONS",
    "VALID_LOCAL_PATH_SPECIFICATION_OPTIONS",
    "VALID_NAME_SPECIFICATION_OPTIONS",
]
