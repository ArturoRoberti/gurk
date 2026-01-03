import ast
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from typing import Iterator, List, Optional, Set, Tuple, TypedDict

from cmstp.cli.utils import CORE_COMMANDS
from cmstp.utils.common import (
    PACKAGE_CONFIG_PATH,
    PACKAGE_SRC_PATH,
    SCRIPT_LANGUAGES,
    CommandKind,
    FilePath,
    ScriptExtension,
)
from cmstp.utils.patterns import PatternCollection


class ScriptBlockTypes(Enum):
    """Types of top-level script blocks."""

    # fmt: off
    CLASS      = auto()
    FUNCTION   = auto()
    ENTRYPOINT = auto()
    IMPORT     = auto()
    OTHER      = auto()
    # fmt: on

    def __repr__(self):
        return self.name


class ScriptBlock(TypedDict):
    """Information about a top-level script block."""

    # fmt: off
    type:  ScriptBlockTypes
    name:  Optional[str]
    lines: Tuple[int, int]  # (start_line, end_line)
    # fmt: on


def get_block_spans(path: FilePath) -> List[ScriptBlock]:
    """
    Returns list of (block_type, start_line, end_line) for top-level script blocks in the given file.

    :param path: Path to the script file
    :type path: FilePath
    :return: List of ScriptBlock dictionaries with block type and line spans
    :rtype: List[ScriptBlock]
    """
    kind = CommandKind.from_script(path)
    source = Path(path).read_text(encoding="utf-8", errors="replace")

    # Find imports (python only)
    imports = []
    if kind == CommandKind.PYTHON:
        tree = ast.parse(source, filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    imports.append(
                        ScriptBlock(
                            type=ScriptBlockTypes.IMPORT,
                            name=alias.name,
                            lines=(node.lineno, node.end_lineno),
                        )
                    )

    # Collect regex patterns for block detection
    func_re = PatternCollection[kind.name].patterns["FUNCTION"]
    class_re = PatternCollection[kind.name].patterns["CLASS"]
    entrypoint_re = PatternCollection[kind.name].patterns["ENTRYPOINT"]

    # Find other blocks
    positions = deepcopy(imports)
    current_block = ScriptBlockTypes.OTHER
    for idx, line in enumerate(source.splitlines(), 1):
        if line.strip() and line.lstrip() == line and not line.startswith("#"):
            m_func = func_re.match(line)
            m_class = class_re.match(line) if class_re else None
            m_entry = entrypoint_re.match(line)
            if m_func:
                positions.append(
                    ScriptBlock(
                        type=ScriptBlockTypes.FUNCTION,
                        name=m_func.group(1),
                        lines=(idx, 0),  # end_line to be filled later
                    )
                )
                current_block = ScriptBlockTypes.FUNCTION
            elif m_class:
                positions.append(
                    ScriptBlock(
                        type=ScriptBlockTypes.CLASS,
                        name=m_class.group(1),
                        lines=(idx, 0),  # end_line to be filled later
                    )
                )
                current_block = ScriptBlockTypes.CLASS
            elif m_entry:
                positions.append(
                    ScriptBlock(
                        type=ScriptBlockTypes.ENTRYPOINT,
                        name=None,
                        lines=(idx, 0),  # end_line to be filled later
                    )
                )
                current_block = ScriptBlockTypes.ENTRYPOINT
            elif any(
                idx in range(b["lines"][0], b["lines"][1] + 1) for b in imports
            ):
                # Import line, already recorded
                continue
            elif (
                kind == CommandKind.BASH
                and (
                    current_block == ScriptBlockTypes.FUNCTION
                    and line.startswith("}")
                )
                or (
                    current_block == ScriptBlockTypes.ENTRYPOINT
                    and line.startswith("fi")
                )
            ):
                # End of bash function or entrypoint block
                positions[-1]["lines"] = (positions[-1]["lines"][0], idx)
                current_block = ScriptBlockTypes.OTHER
            else:
                positions.append(
                    ScriptBlock(
                        type=ScriptBlockTypes.OTHER,
                        name=None,
                        lines=(idx, 0),  # end_line to be filled later
                    )
                )
                current_block = ScriptBlockTypes.OTHER

    # Assign end lines
    positions.sort(key=lambda b: b["lines"][0])
    for i in range(len(positions) - 1):
        if positions[i]["lines"][1] == 0:
            positions[i]["lines"] = (
                positions[i]["lines"][0],
                positions[i + 1]["lines"][0] - 1,
            )
    if positions and positions[-1]["lines"][1] == 0:
        positions[-1]["lines"] = (
            positions[-1]["lines"][0],
            len(source.splitlines()),
        )

    # Merge adjacent IMPORT and OTHER blocks
    merged_positions = []
    for block in positions:
        if (
            merged_positions
            and block["type"]
            in {ScriptBlockTypes.IMPORT, ScriptBlockTypes.OTHER}
            and merged_positions[-1]["type"] == block["type"]
        ):
            # Merge with previous block
            merged_positions[-1]["lines"] = (
                merged_positions[-1]["lines"][0],
                block["lines"][1],
            )
            merged_positions[-1]["name"] = None  # Mixed names
        else:
            merged_positions.append(block)

    return merged_positions


@dataclass(frozen=True)
class Command:
    """Represents a command to be executed, including its script and optional function."""

    # fmt: off
    script:     str           = field()
    function:   Optional[str] = field(default=None)
    check_func: bool          = field(default=True)
    # fmt: on

    def __post_init__(self) -> None:
        # Check 'script'
        if not Path(self.script).is_file():
            raise FileNotFoundError(f"Script file not found: {self.script}")
        try:
            self.kind  # Trigger 'kind' property to validate script type
        except ValueError:
            raise ValueError(
                f"Unsupported script type for file {self.script} - supported "
                f"types: {[ext.name.lower() for ext in ScriptExtension]}"
            )

        # Check 'function'
        blocks = get_block_spans(self.script)
        if self.check_func and self.function is not None:
            available_functions = [
                b["name"]
                for b in blocks
                if b["type"] == ScriptBlockTypes.FUNCTION
            ]
            if self.function not in available_functions:
                raise ValueError(
                    f"'{self.function}' function not found in script "
                    f"{self.script}\nAvailable functions: {available_functions}",
                )

    @cached_property
    def kind(self) -> CommandKind:
        return CommandKind.from_script(self.script)

    def __str__(self) -> str:
        func_suffix = f"@{self.function}" if self.function else ""
        return f"{Path(self.script).stem}{func_suffix}"


def _iter_command_files(
    base_path: Path, script_languages: Optional[Set[str]] = None
) -> Iterator[Path]:
    """
    Yields all files under `<base_path>/scripts/<language>/<command>/`
    if script_languages is provided, else `<base_path>/scripts/<command>/`.

    :param base_path: Path to the base directory
    :type base_path: Path
    :param script_languages: Set of script languages to filter by
    :type script_languages: Optional[Set[str]]
    :return: Iterator of Paths to command files
    :rtype: Iterator[Path]
    """
    if not base_path.exists():
        return

    # Determine starting points
    if script_languages is None:
        # Start directly from base_path
        start_dirs = [base_path]
    else:
        # Start from language directories
        start_dirs = [
            d
            for d in base_path.iterdir()
            if d.is_dir() and d.name.upper() in script_languages
        ]

    # Loop through command directories under starting directories
    for parent_dir in start_dirs:
        for command_dir in parent_dir.iterdir():
            if command_dir.is_dir() and command_dir.name in CORE_COMMANDS:
                for file_path in command_dir.iterdir():
                    if file_path.is_file():
                        yield file_path


def iter_scripts() -> Iterator[Path]:
    """
    Yields all script files under the package scripts directory.

    :return: Iterator of Paths to script files
    :rtype: Iterator[Path]
    """
    scripts_path = PACKAGE_SRC_PATH / "scripts"
    yield from _iter_command_files(scripts_path, SCRIPT_LANGUAGES)


def iter_configs() -> Iterator[Path]:
    """
    Yields all config files under the package config directory.

    :return: Iterator of Paths to config files
    :rtype: Iterator[Path]
    """
    yield from _iter_command_files(PACKAGE_CONFIG_PATH)
