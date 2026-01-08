from dataclasses import dataclass, field

from gurk.plugin.utils import import_plugin


@dataclass(frozen=True)
class ImportArgs:
    # fmt: off
    sources: list[str] = field(metadata={"help": "Local paths or git URLs of the plugin sources to import"})
    update:  bool      = field(metadata={"help": "Update existing plugins if they already exist"}, default=False)
    # fmt: on


# TODO: Add '--recursive' flag to also import dependencies of the imported plugins. Should this be default behavior?
def import_cmd(args: ImportArgs):
    """'import' subcommand used as 'gurk plugin import'"""
    for source in args.sources:
        if not import_plugin(source, args.update):
            print(f"Failed to import plugin from source '{source}'.")
            # TODO: Use logger (error)
            continue
