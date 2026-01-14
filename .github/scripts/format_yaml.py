#!/usr/bin/env python3
import sys
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=2, offset=0)
yaml.Representer.add_representer(
    type(None),
    lambda self, data: self.represent_scalar("tag:yaml.org,2002:null", "null"),
)  # conserve 'null'


def compress_comments(file_path: Path) -> None:
    """
    Compress comment-only files or comment lines between YAML nodes.

    :param file_path: The path to the YAML file to compress
    :type file_path: Path
    """
    lines = file_path.read_text(encoding="utf-8").splitlines()

    compressed = []
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("#"):  # Comment line
            compressed.append(stripped)
        elif stripped:  # YAML content (+ any inline comment)
            compressed.append(ln)
        else:  # Blank line - add max one
            if compressed and compressed[-1].strip() != "":
                compressed.append(ln)

    file_path.write_text("\n".join(compressed) + "\n")


def strip_trailing_whitespace(file_path: Path) -> None:
    """
    Strip trailing whitespace from each line in the given file.

    :param file_path: The path to the YAML file to process
    :type file_path: Path
    """
    # Ensure whitespace consistency
    lines = file_path.read_text(encoding="utf-8").splitlines()
    stripped = [ln.rstrip() for ln in lines]
    file_path.write_text("\n".join(stripped) + "\n", encoding="utf-8")


def format_file(file_path: Path) -> None:
    """
    Format a YAML file while preserving comments.

    :param file_path: The path to the YAML file to format
    :type file_path: Path
    """
    text = file_path.read_text(encoding="utf-8")
    if text == "":
        # Leave empty files completely untouched
        return

    if not file_path.parent == Path(".github/workflows"):
        compress_comments(file_path)

    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)

    if data is not None:
        # Only comments exist; leave as-is
        return

    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)

    # Final cleanup so trailing-whitespace hook has nothing left to fix
    strip_trailing_whitespace(file_path)


if __name__ == "__main__":
    paths = sys.argv[1:]
    for p in paths:
        format_file(Path(p))
