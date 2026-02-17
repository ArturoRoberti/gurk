from pathlib import Path
from typing import Any

import tomli_w
import tomllib

from gurk.lib.utils import PathLike, typecheck


@typecheck
def load_toml(toml_file: PathLike) -> dict[str, Any] | None:
    """
    Load a TOML file.

    :param toml_file: Path to the TOML file to load
    :type toml_file: PathLike
    :return: Content of the TOML file, or None if loading fails
    :rtype: dict[str, Any] | None
    """
    if not Path(toml_file).is_file():
        return None

    with open(toml_file, "rb") as f:
        try:
            return tomllib.load(f) or {}
        except tomllib.TOMLDecodeError:
            return None


@typecheck
def dump_toml(toml_file: PathLike, content: dict[str, Any]) -> None:
    """
    Dump content to a TOML file.

    :param toml_file: Path to the TOML file to dump to
    :type toml_file: PathLike
    :param content: Content to dump
    :type content: dict[str, Any]
    """
    with open(toml_file, "wb") as f:
        tomli_w.dump(content, f)
