import shutil
from pathlib import Path

from gurk.utils.common import PACKAGE_SRC_PATH


def create_cmd():
    """'create' subcommand used as 'gurk plugin create'"""
    shutil.copytree(
        PACKAGE_SRC_PATH / "plugins" / "template",
        Path.cwd() / "my-gurk-plugin",
    )
