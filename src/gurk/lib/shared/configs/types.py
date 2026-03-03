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

from typing import TypeAlias, TypeVar

from ruamel.yaml import YAML as RuamelYAML, CommentedMap

YAML = RuamelYAML()
YAML.preserve_quotes = True
YAML.indent(mapping=2, sequence=2, offset=0)
YAML.Representer.add_representer(
    type(None),
    lambda self, data: self.represent_scalar("tag:yaml.org,2002:null", "null"),
)  # conserve 'null'


# NOTE: '@typecheck' converts 'CommentedMap' to 'dict' at runtime, if annotated
#       as such. This union type should be used to preserve the original type.
K = TypeVar("K")
V = TypeVar("V")
CommentedDict: TypeAlias = CommentedMap[K, V] | dict[K, V]
