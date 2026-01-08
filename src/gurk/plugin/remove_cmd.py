from dataclasses import dataclass, field

from gurk.plugin.utils import remove_plugin


@dataclass(frozen=True)
class RemoveArgs:
    plugins: list[str] = field(
        metadata={"help": "Names of the plugins to remove"}
    )


def remove_cmd(args: RemoveArgs):
    """'remove' subcommand used as 'gurk plugin remove'"""
    for plugin_name in args.plugins:
        remove_plugin(plugin_name)
