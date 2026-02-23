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
