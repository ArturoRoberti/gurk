from pathlib import Path

from gurk.utils.common import CommandKind, stream_print
from gurk.utils.patterns import PatternCollection
from gurk.utils.scripts import ScriptBlockTypes, get_block_spans, iter_scripts


def _check_script_blocks(path: Path) -> bool:
    """
    Check that a script only contains allowed top-level code:
    - Only functions and an entrypoint (and imports for Python)
    - At most one entrypoint, which must be at the end of the script

    NOTE: Any block start with an added comment after will be considered invalid/OTHER.

    :param path: Path to the script file
    :type path: Path
    :return: True if the script meets the criteria, False otherwise
    :rtype: bool
    """
    # Use get_block_spans to find all blocks
    blocks = get_block_spans(path)

    # Error variables
    errors = []
    errors_prefix = "ERROR: "
    errors_prefix_empty = " " * len(errors_prefix)

    # Check there are no CLASS or OTHER blocks
    disallowed_blocks = [
        b
        for b in blocks
        if b["type"] in {ScriptBlockTypes.CLASS, ScriptBlockTypes.OTHER}
    ]
    if disallowed_blocks:
        disallowed_lines = ", ".join(
            str(b["lines"]) for b in disallowed_blocks
        )
        errors.append(
            f"'{path}:{disallowed_blocks[0]['lines'][0]}' contains disallowed "
            f"top-level blocks (not FUNCTION, ENTRYPOINT, or IMPORT).\n"
            f"{errors_prefix_empty}Disallowed lines: {disallowed_lines}"
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
                captured = ", ".join([arg.split(":")[0] for arg in arg_list])
                errors.append(
                    f"'{function_name}' function in '{path}' does "
                    f"not only capture '*args' as an argument, but:\n"
                    f"{errors_prefix_empty}{captured}"
                )

    # Check that there is at most one ENTRYPOINT block and it is at the end
    entrypoints = [
        b for b in blocks if b["type"] == ScriptBlockTypes.ENTRYPOINT
    ]
    if len(entrypoints) > 1:
        entrypoint_lines = ", ".join(str(b["lines"]) for b in entrypoints)
        errors.append(
            f"'{path}:{entrypoints[0]['lines'][0]}' contains more than one ENTRYPOINT block.\n"
            f"{errors_prefix_empty}ENTRYPOINT blocks at lines: {entrypoint_lines}"
        )

    # Check that ENTRYPOINT is at the end
    if entrypoints and blocks[-1]["type"] != ScriptBlockTypes.ENTRYPOINT:
        entrypoint_lines = ", ".join(str(b["lines"]) for b in entrypoints)
        errors.append(
            f"'{path}:{entrypoints[0]['lines'][0]}' ENTRYPOINT block in {path} is not at the end of the script.\n"
            f"{errors_prefix_empty}ENTRYPOINT block(s) at lines: {entrypoint_lines}"
        )

    # Report errors if any
    if errors:
        for error in errors:
            stream_print(errors_prefix + error, stderr=True)
        return False
    else:
        return True


def test_package_scripts() -> None:
    """Test that the package scripts are valid."""
    assert all(
        _check_script_blocks(path) for path in iter_scripts()
    ), "One or more scripts contain disallowed top-level blocks"
