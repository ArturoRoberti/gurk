import ast
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from typing import TypedDict

from gurk.lib.utils.common import CommandKind, PathLike, ScriptExtension
from gurk.lib.utils.patterns import PatternCollection


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
    name:  str | None
    lines: tuple[int, int]  # (start_line, end_line)
    # fmt: on


def get_block_spans(path: PathLike) -> list[ScriptBlock]:
    """
    Returns list of (block_type, start_line, end_line) for top-level script blocks in the given file.

    :param path: Path to the script file
    :type path: PathLike
    :return: List of ScriptBlock dictionaries with block type and line spans
    :rtype: list[ScriptBlock]
    """
    kind = CommandKind.from_script(path)
    source = Path(path).read_text(encoding="utf-8", errors="replace")

    # Find imports
    imports = []
    if kind == CommandKind.PYTHON:
        ## Python imports via AST
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
    elif kind == CommandKind.BASH:
        ## Bash imports via regex
        import_re = PatternCollection.BASH.patterns["IMPORT"]
        for idx, line in enumerate(source.splitlines(), 1):
            m_import = import_re.match(line)
            if m_import:
                imports.append(
                    ScriptBlock(
                        type=ScriptBlockTypes.IMPORT,
                        name=m_import.group(1),
                        lines=(idx, idx),
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

    # Set IMPORT blocks that appear after non-import as OTHER (bash only - TODO: why not python?)
    non_import_found = False
    if kind == CommandKind.BASH:
        for block in positions:
            if block["type"] != ScriptBlockTypes.IMPORT:
                non_import_found = True
            elif non_import_found and block["type"] == ScriptBlockTypes.IMPORT:
                block["type"] = ScriptBlockTypes.OTHER

    # Merge adjacent OTHER blocks for readability
    merged_positions = []
    for block in positions:
        if (
            merged_positions
            and block["type"] == ScriptBlockTypes.OTHER
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
    function:   str | None    = field(default=None)
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


def check_script_blocks(path: Path) -> list[str]:
    """
    Check that a script only contains allowed top-level code:
    - Only functions and an entrypoint (and imports for Python)
    - At most one entrypoint, which must be at the end of the script

    NOTE: Any block start with an added comment after will be considered invalid/OTHER.

    :param path: Path to the script file
    :type path: Path
    :return: List of error messages if the script does not meet the criteria, empty list otherwise
    :rtype: list[str]
    """
    # Use get_block_spans to find all blocks
    blocks = get_block_spans(path)

    # Error tracking
    errors = []

    # Check there are no OTHER blocks
    disallowed_blocks = [
        b for b in blocks if b["type"] == ScriptBlockTypes.OTHER
    ]
    if disallowed_blocks:
        disallowed_lines = ", ".join(
            str(b["lines"]) for b in disallowed_blocks
        )
        errors.append(
            f"'{path}:{disallowed_blocks[0]['lines'][0]}' contains disallowed top-level "
            f"blocks (not FUNCTION, ENTRYPOINT, or IMPORT) at lines: {disallowed_lines}"
        )

    # Check that each function name is unique
    function_names = [
        b["name"] for b in blocks if b["type"] == ScriptBlockTypes.FUNCTION
    ]
    duplicates_names = [
        name for name in function_names if function_names.count(name) > 1
    ]
    if duplicates_names:
        errors.append(
            f"'{path}' contains duplicate function names: {', '.join(duplicates_names)}"
        )

    # Check that python functions only capture '*args'
    if CommandKind.from_script(path.name) == CommandKind.PYTHON:
        pattern = PatternCollection.PYTHON.patterns["FUNCTION"]
        matches = [
            match
            for line in path.read_text().splitlines()
            if (match := pattern.search(line.strip()))
        ]
        for match in matches:
            # Extract top-level function names and args
            function_name, args = match.groups()
            if function_name not in function_names:
                # Skip nested functions
                continue

            # Check args
            arg_list = [arg.strip() for arg in args.split(",") if arg.strip()]
            if not (
                len(arg_list) == 1 and arg_list[0].split(":")[0] == "*args"
            ):
                captured = ", ".join(
                    [repr(arg.split(":")[0]) for arg in arg_list]
                )
                errors.append(
                    f"'{function_name}' function in '{path}' does not only "
                    f"capture '*args' as an argument, but: {captured}"
                )

    # Check that there is at most one ENTRYPOINT block and it is at the end
    entrypoints = [
        b for b in blocks if b["type"] == ScriptBlockTypes.ENTRYPOINT
    ]
    if len(entrypoints) > 1:
        entrypoint_lines = ", ".join(str(b["lines"]) for b in entrypoints)
        errors.append(
            f"'{path}:{entrypoints[0]['lines'][0]}' contains more "
            f"than one ENTRYPOINT block at lines: {entrypoint_lines}"
        )

    # Check that ENTRYPOINT is at the end
    if entrypoints and blocks[-1]["type"] != ScriptBlockTypes.ENTRYPOINT:
        entrypoint_lines = ", ".join(str(b["lines"]) for b in entrypoints)
        errors.append(
            f"'{path}:{entrypoints[0]['lines'][0]}' ENTRYPOINT block in {path} "
            f"is not at the end of the script, but at lines: {entrypoint_lines}"
        )

    # Return errors if any
    return errors
