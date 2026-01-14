#!/usr/bin/env python3
"""
JSONC formatter (// comments only) using commentjson
Preserves:
- top comments
- leading comments (above keys)
- inline comments (same line)
- bottom comments (after final closing brace)
Uses full key paths to avoid collisions.
"""
import re
import sys
from pathlib import Path

import commentjson

KEY_RE = re.compile(r'^\s*"([^"]+)":')


def split_content_and_comment(line: str) -> tuple[str, str | None]:
    """
    Split a line into content and inline comment.

    :param line: The line of text to split
    :type line: str
    :return: A tuple containing the content part and the inline comment (if any)
    :rtype: tuple[str, str | None]
    """
    in_string = False
    escaped = False
    for i, ch in enumerate(line):
        if ch == '"' and not escaped:
            in_string = not in_string
        elif ch == "\\" and not escaped:
            escaped = True
            continue
        elif (
            not in_string
            and ch == "/"
            and i + 1 < len(line)
            and line[i + 1] == "/"
        ):
            # Found real comment start outside string
            return line[:i].rstrip(), line[i:].strip()
        escaped = False
    return line.rstrip(), None


def extract_comments(
    lines: list[str],
) -> tuple[list[str], list[str], dict[str, list[str]], dict[str, str]]:
    """
    Extract comments from JSONC lines.

    :param lines: The lines of the JSONC file
    :type lines: list[str]
    :return: A tuple containing top comments, bottom comments, leading comments, and inline comments
    :rtype: tuple[list[str], list[str], dict[str, list[str]], dict[str, str]]
    """
    top, bottom, leading, inline = [], [], {}, {}
    cur_comments, path_stack = [], []
    in_obj = False

    def full_path(key=None):
        return ".".join(path_stack + ([key] if key else []))

    for line in lines:
        content, comment = split_content_and_comment(line)

        # Empty or comment-only line
        if not content:
            if not in_obj:
                top.append(line.rstrip())
            else:
                cur_comments.append(line.strip())
            continue

        if content.startswith("{"):
            in_obj = True
            continue

        if content.startswith("}"):
            # Keep trailing comment for next key
            if comment:
                cur_comments.append(comment)
            if path_stack:
                path_stack.pop()
            continue

        m = KEY_RE.match(content)
        if m:
            key = m.group(1)
            fp = full_path(key)
            if cur_comments:
                leading[fp] = cur_comments.copy()
                cur_comments = []
            if comment:
                inline[fp] = comment
            if "{" in content:
                path_stack.append(key)
        elif comment:
            cur_comments.append(comment)

    # Any remaining comments after last line
    bottom.extend(cur_comments)
    return top, leading, inline, bottom


def format_jsonc_file(path: Path) -> None:
    """
    Format a JSONC file while preserving comments.

    :param path: The path to the JSONC file to format
    :type path: Path
    """
    lines = [ln + "\n" for ln in path.read_text().splitlines()]
    top, leading, inline, bottom = extract_comments(lines)

    # Preserve pure comment files
    non_empty_lines = [ln for ln in lines if ln.strip()]
    non_comment_lines = [
        ln for ln in non_empty_lines if not ln.strip().startswith("//")
    ]
    if not non_comment_lines:
        out_lines = [ln.lstrip().rstrip() for ln in lines if ln.strip()]
        path.write_text("\n".join(out_lines) + "\n")
        return

    # Try parsing JSONC content to check validity
    content = path.read_text()
    try:
        data = commentjson.loads(content)
        if not data:
            # Empty JSON content: keep comments
            out_lines = [ln.lstrip().rstrip() for ln in lines if ln.strip()]
            path.write_text("\n".join(out_lines) + "\n")
            return
    except commentjson.JSONLibraryException:
        # Malformed JSON: fail
        raise

    # Load and format content
    formatted = commentjson.dumps(data, indent=2).splitlines()

    # Re-dump content with comments preserved
    opening, closing = formatted[0], formatted[-1]
    out_lines = top + [opening]
    stack = []

    for line in formatted[1:-1]:
        stripped = line.strip()
        if stripped.startswith("}"):
            if stack:
                stack.pop()
            out_lines.append(line)
            continue

        m = KEY_RE.match(line)
        if m:
            key = m.group(1)
            fp = ".".join(stack + [key])
            indent = line[: line.index('"')]
            if fp in leading:
                for c in leading[fp]:
                    out_lines.append(indent + c.strip())
            out_lines.append(line)
            if fp in inline:
                out_lines[-1] += " " + inline[fp]
            if line.strip().endswith("{"):
                stack.append(key)
        else:
            out_lines.append(line)

    if len(formatted) > 1:  # Non-empty object
        out_lines.append(closing)
    out_lines.extend(bottom)
    out_lines = [
        ln for ln in out_lines if ln.strip()
    ]  # Remove all empty lines (except one at end)
    path.write_text("\n".join(out_lines) + "\n")


def main(argv):
    failed_files = []
    for p in argv:
        path = Path(p)
        try:
            format_jsonc_file(path)
        except Exception:
            failed_files.append(p)

    if failed_files:
        print("Auto-format JSON(C) files failed for:")
        for f in failed_files:
            print(f"  {f}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
