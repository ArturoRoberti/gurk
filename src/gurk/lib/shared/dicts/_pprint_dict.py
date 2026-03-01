from typing import Any

from gurk.lib.utils import typecheck

from .pprint_utils import _combine_lines


@typecheck
def _render_dict_value(
    value: Any,
    *,
    tag: str,
    color: str,
    capitalize: bool,
    indent: int,
    indent_step: int,
) -> list[str]:
    """
    Render a single dictionary value as formatted output lines.

    Handles different value types: empty/falsy values, nested dicts, sequences,
    and scalar values. Each type receives appropriate formatting and indentation.

    :param value: The value to render
    :type value: Any
    :param tag: Pre-formatted key tag with color markup
    :type tag: str
    :param color: Rich color name for key display
    :type color: str
    :param capitalize: Whether to capitalize string keys
    :type capitalize: bool
    :param indent: Current indentation level
    :type indent: int
    :param indent_step: Indentation per nesting level
    :type indent_step: int
    :return: List of formatted output lines
    :rtype: list[str]
    """
    lines: list[str] = []

    # Falsy values (None, [], {}, 0, etc.) displayed inline
    if not value:
        lines.append(f"{tag} {repr(value)}")

    # Nested dicts: render recursively with increased indentation
    elif isinstance(value, dict):
        lines.append(tag)
        lines.append(
            _render_dict_structure(
                value,
                color=color,
                capitalize=capitalize,
                indent=indent + indent_step,
                indent_step=indent_step,
            )
        )

    # Sequences: list items as bullet points, recurse for dict items
    elif isinstance(value, (list, tuple, set)):
        lines.append(tag)
        for item in value:
            if isinstance(item, dict):
                lines.append(
                    _render_dict_structure(
                        item,
                        color=color,
                        capitalize=capitalize,
                        indent=indent + indent_step,
                        indent_step=indent_step,
                    )
                )
            else:
                lines.append(" " * (indent + indent_step) + f"- {item}")

    # Scalars (str, int, etc.): displayed inline with key
    else:
        lines.append(f"{tag} {value}")

    return lines


@typecheck
def _render_dict_structure(
    obj: Any,
    *,
    color: str = "white",
    capitalize: bool = False,
    indent: int = 0,
    indent_step: int = 2,
) -> str:
    """
    Render a runtime dictionary structure with rich text markup.

    Recursively formats dicts and nested structures with aligned key:value pairs,
    optional key capitalization, and configurable indentation.

    :param obj: Dictionary to render (or any non-dict value for fallback rendering)
    :type obj: Any
    :param color: Rich color name for key tags
    :type color: str
    :param capitalize: Capitalize string keys
    :type capitalize: bool
    :param indent: Current indentation in spaces
    :type indent: int
    :param indent_step: Spaces per indentation level
    :type indent_step: int
    :return: Formatted string with single trailing newline
    :rtype: str
    """
    # Non-dict fallback: just render with indent and repr()
    if not isinstance(obj, dict):
        return " " * indent + repr(obj) + "\n"

    items = list(obj.items())

    # Empty dict: return empty string
    if not items:
        return ""

    # Calculate max key length for alignment
    maxlen = max((len(str(k)) for k, _ in items), default=0)
    lines: list[str] = []

    # Process each key-value pair
    for k, v in items:
        # Format key display (optionally capitalized for string keys)
        key_display = (
            k.capitalize() if capitalize and isinstance(k, str) else str(k)
        )

        # Create colorized key tag with fixed-width alignment
        tag = f"{' ' * indent}[{color}]{key_display:<{maxlen}}:[/{color}]"

        # Render the value and extend lines list
        lines.extend(
            _render_dict_value(
                v,
                tag=tag,
                color=color,
                capitalize=capitalize,
                indent=indent,
                indent_step=indent_step,
            )
        )

    return _combine_lines(lines)
