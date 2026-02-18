from pathlib import Path
from typing import Any

import tomli_w
import tomllib

from gurk.lib.utils import PathLike, typecheck


@typecheck
def load_toml(
    toml_file_or_str: PathLike, *, from_str: bool = False
) -> dict[str, Any] | None:
    """
    Load TOML content.

    :param toml_file_or_str: Path to the TOML file to load or a string containing TOML content (if 'from_str' is True)
    :type toml_file_or_str: PathLike
    :param from_str: Whether 'toml_file_or_str' is a string containing TOML content (True) or a file path (False, default)
    :type from_str: bool
    :return: Content of the TOML file, or None if loading fails
    :rtype: dict[str, Any] | None
    """
    if from_str:
        try:
            return tomllib.loads(toml_file_or_str) or {}
        except tomllib.TOMLDecodeError:
            return None
    else:
        if not Path(toml_file_or_str).is_file():
            return None
        with open(toml_file_or_str, "rb") as f:
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
