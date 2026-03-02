# Copyright 2026 Arturo Roberti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import types
from typing import (
    Any,
    NotRequired,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

from rich.markup import escape

from gurk.lib.utils import typecheck

from .pprint_utils import _combine_lines


def _type_to_str(tp: Any) -> str:
    """
    Convert a type annotation to a human-friendly string representation.

    Handles common typing constructs like Union, dict, list, set, tuple, and basic types.

    :param tp: The type annotation to convert
    :type tp: Any
    :return: Human-friendly string representation of the type
    :rtype: str
    """
    # Handle None type
    if tp is None or tp is type(None):
        return "None"

    # Handle built-in types
    if isinstance(tp, type):
        return tp.__name__

    # Handle generic types (Union, dict, list, etc.)
    origin = get_origin(tp)
    args = get_args(tp)

    # Union types: display as 'A | B | C'
    if origin in (Union, types.UnionType):
        return " | ".join(_type_to_str(a) for a in args)

    # dict[K, V] types
    if origin is dict:
        return (
            f"dict[{_type_to_str(args[0])}, {_type_to_str(args[1])}]"
            if args
            else "dict"
        )

    # Sequence types: list[T], set[T], tuple[T]
    if origin in (list, set, tuple):
        name = origin.__name__
        return f"{name}[{_type_to_str(args[0])}]" if args else name

    # Fallback for complex types
    return str(tp)


def _contains_typeddict(tp: Any) -> bool:
    """
    Recursively check if a type annotation contains a TypedDict (directly or nested).

    Inspects direct TypedDict types, value types in dict[K, V], element types in
    list/set/tuple, and member types in Union.

    :param tp: Type annotation to check
    :type tp: Any
    :return: True if TypedDict is found anywhere in the type structure
    :rtype: bool
    """
    # Direct TypedDict
    if is_typeddict(tp):
        return True

    origin = get_origin(tp)
    args = get_args(tp)

    # No args means no nesting to check
    if not args:
        return False

    # Check value type of dict[K, V]
    if origin is dict:
        return _contains_typeddict(args[1])

    # Check element types of sequences
    if origin in (list, set, tuple):
        return _contains_typeddict(args[0])

    # Check all member types of Union
    if origin in (Union, types.UnionType):
        return any(_contains_typeddict(a) for a in args)

    return False


@typecheck
def _render_generic_type(
    origin: Any,
    args: tuple[Any, ...],
    *,
    color: str,
    indent: int,
    indent_step: int,
    pad: str,
) -> list[str]:
    """
    Render generic type annotations like dict[K, V], list[T], etc.

    Handles parameterized types that are not TypedDict themselves but may contain them.
    Recursively renders nested TypedDict types.

    :param origin: Generic type origin (dict, list, set, tuple, etc.)
    :type origin: Any
    :param args: Type arguments (e.g., [K, V] for dict[K, V])
    :type args: tuple[Any, ...]
    :param color: Rich color name for output
    :type color: str
    :param indent: Current indentation in spaces
    :type indent: int
    :param indent_step: Spaces per indentation level
    :type indent_step: int
    :param pad: Pre-calculated padding string
    :type pad: str
    :return: List of formatted output lines
    :rtype: list[str]
    """
    lines: list[str] = []

    # Handle dict[K, V] - show key type then recursively render value type
    if origin is dict and args:
        ktype, vtype = args
        lines.append(pad + f"<{_type_to_str(ktype)}>:")
        nested = _render_typed_dict_structure(
            vtype,
            color=color,
            indent=indent + indent_step,
            indent_step=indent_step,
        )
        lines.append(nested.rstrip("\n"))

    # Handle sequence[T] - show list marker then recursively render element type
    if origin in (list, set, tuple) and args:
        elem = args[0]
        lines.append(pad + "-")
        lines.append(
            _render_typed_dict_structure(
                elem,
                color=color,
                indent=indent + indent_step,
                indent_step=indent_step,
            )
        )

    return lines


@typecheck
def _prepare_typeddict_items(hints: dict[str, Any]) -> list[tuple[str, Any]]:
    """
    Prepare TypedDict items for rendering with display names.

    Extracts field names and their annotations from TypedDict hints, handling
    the NotRequired wrapper to expose it in the display name while unwrapping
    the core annotation.

    :param hints: Type hints dict from TypedDict
    :type hints: dict[str, Any]
    :return: List of (display_name, core_annotation) tuples
    :rtype: list[tuple[str, Any]]
    """
    items = []
    for name, ann in hints.items():
        # Check if annotation is wrapped with NotRequired
        is_nr = get_origin(ann) is NotRequired

        # Unwrap NotRequired to get the core type
        core = get_args(ann)[0] if is_nr else ann

        # Add "(NotRequired)" suffix to display name if applicable
        display = name + (" (NotRequired)" if is_nr else "")

        items.append((display, core))

    return items


@typecheck
def _render_nested_typeddict(
    tag: str,
    ann: Any,
    *,
    color: str,
    indent: int,
    indent_step: int,
) -> list[str]:
    """
    Render a nested TypedDict annotation.

    Outputs the field tag followed by indented recursive rendering
    of the TypedDict structure.

    :param tag: Pre-formatted field tag with color markup
    :type tag: str
    :param ann: The TypedDict type annotation
    :type ann: Any
    :param color: Rich color name for nested output
    :type color: str
    :param indent: Current indentation in spaces
    :type indent: int
    :param indent_step: Spaces per indentation level
    :type indent_step: int
    :return: List of formatted output lines
    :rtype: list[str]
    """
    lines: list[str] = [tag]
    lines.append(
        _render_typed_dict_structure(
            ann,
            color=color,
            indent=indent + indent_step,
            indent_step=indent_step,
        )
    )
    return lines


@typecheck
def _render_dict_annotation(
    tag: str,
    ktype: Any,
    vtype: Any,
    *,
    color: str,
    indent: int,
    indent_step: int,
) -> list[str]:
    """
    Render dict[K, V] type annotation for a TypedDict field.

    If the value type contains a TypedDict, recursively render it with
    increased indentation. Otherwise, show both types inline.

    :param tag: Pre-formatted field tag with color markup
    :type tag: str
    :param ktype: Key type annotation
    :type ktype: Any
    :param vtype: Value type annotation
    :type vtype: Any
    :param color: Rich color name for nested output
    :type color: str
    :param indent: Current indentation in spaces
    :type indent: int
    :param indent_step: Spaces per indentation level
    :type indent_step: int
    :return: List of formatted output lines
    :rtype: list[str]
    """
    lines: list[str] = [tag]

    if _contains_typeddict(vtype):
        # Nested TypedDict in value: show key type then recurse
        lines.append(
            " " * (indent + indent_step) + f"<{_type_to_str(ktype)}>:"
        )
        lines.append(
            _render_typed_dict_structure(
                vtype,
                color=color,
                indent=indent + indent_step * 2,
                indent_step=indent_step,
            )
        )
    else:
        # Simple types: show both key and value inline
        lines.append(
            " " * (indent + indent_step)
            + f"<{_type_to_str(ktype)}>: {_type_to_str(vtype)}"
        )

    return lines


@typecheck
def _render_sequence_annotation(
    tag: str,
    origin: Any,
    elem: Any,
    *,
    color: str,
    indent: int,
    indent_step: int,
) -> list[str]:
    """
    Render list/set/tuple type annotation for a TypedDict field.

    If the element type contains a TypedDict, recursively render it.
    Otherwise, show the element type inline with the sequence type name.

    :param tag: Pre-formatted field tag with color markup
    :type tag: str
    :param origin: Sequence type (list, set, or tuple)
    :type origin: Any
    :param elem: Element type annotation
    :type elem: Any
    :param color: Rich color name for nested output
    :type color: str
    :param indent: Current indentation in spaces
    :type indent: int
    :param indent_step: Spaces per indentation level
    :type indent_step: int
    :return: List of formatted output lines
    :rtype: list[str]
    """
    lines: list[str] = []

    if _contains_typeddict(elem):
        # Nested TypedDict in elements: show sequence type then recurse
        lines.append(tag)
        lines.append(" " * (indent + indent_step) + "-")
        lines.append(
            _render_typed_dict_structure(
                elem,
                color=color,
                indent=indent + indent_step * 2,
                indent_step=indent_step,
            )
        )
    else:
        # Simple element type: show inline with sequence name
        lines.append(
            f"{tag} {origin.__name__}{escape(f'[{_type_to_str(elem)}]')}"
        )

    return lines


@typecheck
def _render_union_annotation(tag: str, args: tuple[Any, ...]) -> list[str]:
    """
    Render Union type annotation for a TypedDict field.

    Shows each union member type, using "<...>" placeholder for any
    members that are TypedDicts (to avoid expanding them inline).

    :param tag: Pre-formatted field tag with color markup
    :type tag: str
    :param args: Union member type annotations
    :type args: tuple[Any, ...]
    :return: List with single line containing union representation
    :rtype: list[str]
    """
    parts = [
        _type_to_str(a) if not _contains_typeddict(a) else "<...>"
        for a in args
    ]
    return [f"{tag} " + " | ".join(parts)]


@typecheck
def _render_annotation(
    tag: str,
    ann: Any,
    *,
    color: str,
    indent: int,
    indent_step: int,
) -> list[str]:
    """
    Dispatch-render a type annotation based on its structure.

    Routes different annotation types to their specialized renderers:
    TypedDict (nested), dict[K, V] (dict-specific), list/set/tuple (sequence),
    Union (union), or simple types (inline).

    :param tag: Pre-formatted field tag with color markup
    :type tag: str
    :param ann: Type annotation to render
    :type ann: Any
    :param color: Rich color name for nested output
    :type color: str
    :param indent: Current indentation in spaces
    :type indent: int
    :param indent_step: Spaces per indentation level
    :type indent_step: int
    :return: List of formatted output lines
    :rtype: list[str]
    """
    origin = get_origin(ann)
    args = get_args(ann)

    # Nested TypedDict
    if is_typeddict(ann):
        return _render_nested_typeddict(
            tag, ann, color=color, indent=indent, indent_step=indent_step
        )

    # dict[K, V] with special handling for TypedDict values
    if origin is dict and args:
        ktype, vtype = args
        return _render_dict_annotation(
            tag,
            ktype,
            vtype,
            color=color,
            indent=indent,
            indent_step=indent_step,
        )

    # list/set/tuple with special handling for TypedDict elements
    if origin in (list, set, tuple) and args:
        elem = args[0]
        return _render_sequence_annotation(
            tag,
            origin,
            elem,
            color=color,
            indent=indent,
            indent_step=indent_step,
        )

    # Union types
    if origin in (Union, types.UnionType):
        return _render_union_annotation(tag, args)

    # Simple scalar types: just display the type name
    return [f"{tag} {_type_to_str(ann)}"]


@typecheck
def _render_typed_dict_structure(
    obj: Any,
    *,
    color: str,
    indent: int,
    indent_step: int,
) -> str:
    """
    Render a TypedDict or generic type structure with full type annotations.

    Handles TypedDict objects by extracting field definitions and rendering each
    with its type annotation, handling NotRequired, nested TypedDicts, etc.
    Also recursively renders parameterized types like dict[K, V] or list[T].

    :param obj: TypedDict class or generic type to render
    :type obj: Any
    :param color: Rich color name for field tags
    :type color: str
    :param indent: Current indentation in spaces
    :type indent: int
    :param indent_step: Spaces per indentation level
    :type indent_step: int
    :return: Formatted string with single trailing newline
    :rtype: str
    """
    pad = " " * indent
    lines: list[str] = []

    if not is_typeddict(obj):
        # Generic type (not a TypedDict): dict[K, V], list[T], etc.
        origin = get_origin(obj)
        args = get_args(obj)
        lines.extend(
            _render_generic_type(
                origin,
                args,
                color=color,
                indent=indent,
                indent_step=indent_step,
                pad=pad,
            )
        )
    else:
        # TypedDict: render all fields with their type annotations
        hints = get_type_hints(obj, include_extras=True)

        # Empty TypedDict: return empty string
        if not hints:
            return ""

        # Prepare field items with proper display names
        items = _prepare_typeddict_items(hints)

        # Calculate max field name length for alignment
        maxlen = max((len(n) for n, _ in items), default=0)

        # Render each field
        for disp, ann in items:
            # Create colorized field tag with fixed-width alignment
            tag = f"{pad}[{color}]{disp:<{maxlen}}:[/{color}]"

            # Dispatch to appropriate annotation renderer
            lines.extend(
                _render_annotation(
                    tag,
                    ann,
                    color=color,
                    indent=indent,
                    indent_step=indent_step,
                )
            )

    return _combine_lines(lines)
