from dataclasses import dataclass, field

from gurk.plugin.utils import check_local_plugin


@dataclass(frozen=True)
class CheckArgs:
    # fmt: off
    paths:         list[str] = field(metadata={"help": "Local paths of custom plugins to check"})
    check_imports: bool      = field(metadata={"help": "Also check imported plugins"}, default=False)
    # fmt: on


def check_cmd(args: CheckArgs):
    """'check' subcommand used as 'gurk plugin check'"""
    for source in args.paths:
        if not check_local_plugin(source, args.check_imports):
            print(f"Plugin source '{source}' is invalid.")
        else:
            print(f"Plugin source '{source}' is valid.")
