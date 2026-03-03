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

# flake8: noqa: F401
from .resolved.args import (
    ResolvedArgsDefinition,
    ResolvedArgsDefinitionCollection,
)
from .resolved.combined import ResolvedTaskDict, ResolvedTaskDictCollection
from .resolved.custom import (
    ResolvedCustomTaskDict,
    ResolvedCustomTaskDictCollection,
)
from .resolved.defined import (
    ResolvedDefaultTaskDict,
    ResolvedDefaultTaskDictCollection,
)
from .unresolved.args import ArgsDefinition, ArgsDefinitionCollection
from .unresolved.combined import TaskDict, TaskDictCollection
from .unresolved.custom import CustomTaskDict, CustomTaskDictCollection
from .unresolved.defined import DefaultTaskDict, DefaultTaskDictCollection
