import shutil
from pathlib import Path

from gurk.utils.cli import CleanArgumentParser
from gurk.utils.common import PACKAGE_SRC_PATH


def main(argv, prog, description):
    parser = CleanArgumentParser(prog=prog, description=description)
    parser.parse_args(argv)

    # Copy the template plugin to the current working directory
    shutil.copytree(
        PACKAGE_SRC_PATH / "plugins" / "template",
        Path.cwd() / "template-gurk-plugin",
    )
