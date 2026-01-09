import inspect
import pkgutil
import traceback
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from gurk import plugin
from gurk.lib.core.plugin_utils import create_subparser
from gurk.lib.logger import Logger, LoggerSeverity


def main(argv, prog, description):
    parser = ArgumentParser(
        prog=prog,
        description=description,
        formatter_class=lambda prog: ArgumentDefaultsHelpFormatter(
            prog=prog,
            max_help_position=60,
        ),
    )
    # TODO: Allow subparser width to be increased
    subparsers = parser.add_subparsers(
        title="subcommands", dest="subcommand", required=True
    )

    # Dynamically load all plugin subcommands
    for _, name, _ in pkgutil.iter_modules(
        plugin.__path__, plugin.__name__ + "."
    ):
        if name.endswith("_cmd"):
            create_subparser(subparsers, name)

    # Parse args and call the appropriate function
    args = parser.parse_args(argv)
    sig = inspect.signature(args.func)
    if sig.parameters:
        args.func(args)
    else:
        args.func()

    try:
        pass

    except (KeyboardInterrupt, Exception) as e:
        traceback_str = traceback.format_exc()
        traceback_msg = (
            f"An Exception occured: {e.__class__.__name__} - {e}\n\n{traceback_str}"
            if str(e).strip()
            else ""
        )
        interrupt_msg = (
            "Process interrupted by user"
            if isinstance(e, KeyboardInterrupt)
            else traceback_msg
        )
        Logger.logrichprint(LoggerSeverity.FATAL, interrupt_msg, newline=True)
