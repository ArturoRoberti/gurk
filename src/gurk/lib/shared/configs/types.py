from ruamel.yaml import YAML as RuamelYAML

YAML = RuamelYAML()
YAML.preserve_quotes = True
YAML.indent(mapping=2, sequence=2, offset=0)
YAML.Representer.add_representer(
    type(None),
    lambda self, data: self.represent_scalar("tag:yaml.org,2002:null", "null"),
)  # conserve 'null'
