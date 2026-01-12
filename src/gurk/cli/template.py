import shutil
from pathlib import Path

from gurk.lib.core.plugin_utils import GurkArgumentParser
from gurk.lib.utils.common import PACKAGE_SRC_PATH


def main(argv, prog, description):
    parser = GurkArgumentParser(
        prog=prog,
        description=description,
        add_verbose_arg=False,
        add_non_interactive_arg=False,
    )
    parser.parse_args(argv)

    # Copy the template plugin to the current working directory
    shutil.copytree(
        PACKAGE_SRC_PATH / "plugins" / "template",
        Path.cwd() / "template-gurk-plugin",
    )
