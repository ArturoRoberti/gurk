from gurk.lib.utils import typecheck


@typecheck
def _combine_lines(lines: list[str]) -> str:
    """
    Combine a list of lines into a single string with normalized newlines.

    Strips trailing newlines from each line, joins with single newline separators,
    and ensures exactly one trailing newline at the end.

    :param lines: List of line strings (may have trailing newlines)
    :type lines: list[str]
    :return: Combined string with single trailing newline
    :rtype: str
    """
    out = "\n".join(line.rstrip("\n") for line in lines)
    return out + ("\n" if not out.endswith("\n") else "")
