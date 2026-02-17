from typing import IO, Any, Literal, overload

from rich import print as _richprint

from gurk.lib.utils import typecheck


@typecheck
def richprint(
    message: str, color: str | None = None, file: IO[str] | None = None
) -> None:
    """
    Print a rich-formatted message with optional color.

    :param message: The message to print
    :type message: str
    :param color: Optional color for the message
    :type color: str | None
    :param file: The output file (stdout/stderr). If None, defaults to stdout.
    :type file: IO[str] | None
    """
    if color:
        _richprint(f"[{color}]{message}[/{color}]", file=file)
    else:
        _richprint(message, file=file)


@typecheck
def padded_print(
    text: str,
    color: str = "white",
    total_length: int = 128,
    top: bool = True,
    bottom: bool = True,
    file: IO[str] | None = None,
) -> None:
    """
    Print text padded with "=" signs to center it within a specified total length.

    :param text: Text to be printed
    :type text: str
    :param color: Color of the text
    :type color: str
    :param total_length: Total length of the printed line including padding
    :type total_length: int
    :param top: Whether to print the top padding line
    :type top: bool
    :param bottom: Whether to print the bottom padding line
    :type bottom: bool
    :param file: The output file (stdout/stderr). If None, defaults to stdout.
    :type file: IO[str] | None
    """
    # Top bar
    if top:
        richprint("=" * total_length, color=color, file=file)

    # Calculate how many "=" signs are needed in the middle
    #   Subtract 2 for extra spaces
    remaining_length = total_length - len(text) - 2
    if remaining_length < 0:
        richprint(f"{text}", color=color, file=file)
    else:
        left_pad = remaining_length // 2
        right_pad = remaining_length - left_pad
        richprint(
            f"{'=' * left_pad} {text} {'=' * right_pad}",
            color=color,
            file=file,
        )
    # Bottom bar
    if bottom:
        richprint("=" * total_length, color=color, file=file)


@overload
def pprint_dict(
    dct: dict[str, Any],
    *,
    color: str = ...,
    capitalize: bool = ...,
    indent: int = ...,
    indent_step: int = ...,
    as_str: Literal[False] = ...,
) -> None:
    ...


@overload
def pprint_dict(
    dct: dict[str, Any],
    *,
    color: str = ...,
    capitalize: bool = ...,
    indent: int = ...,
    indent_step: int = ...,
    as_str: Literal[True] = ...,
) -> str:
    ...


@typecheck
def pprint_dict(
    dct: dict[str, Any],
    *,
    color: str = "white",
    capitalize: bool = False,
    indent: int = 0,
    indent_step: int = 2,
    as_str: bool = False,
) -> str | None:
    """
    Pretty-print a dictionary of arbitrary depth with aligned keys and colored output.

    :param dct: Dictionary to pretty-print
    :type dct: dict[str, Any]
    :param color: Color name for the keys
    :type color: str
    :param capitalize: Whether to capitalize string keys
    :type capitalize: bool
    :param indent: Base indentation (spaces)
    :type indent: int
    :param indent_step: Spaces added per nesting level
    :type indent_step: int
    :param as_str: Whether to return the formatted string instead of printing it
    :type as_str: bool
    :return: The formatted string if as_str is True, otherwise None
    :rtype: str | None
    """
    if not isinstance(dct, dict):
        rmsg = f"{' ' * indent}{dct}"
        if as_str:
            return f"{rmsg}\n"
        else:
            _richprint(rmsg)
            return

    maxlen = max((len(str(k)) for k in dct), default=0)

    rmsg = ""
    for k, v in dct.items():
        key = k.capitalize() if capitalize and isinstance(k, str) else k
        pad = " " * indent
        msg = f"{pad}[{color}]{key:<{maxlen}}:[/{color}]"
        if not v:
            rmsg += f"{msg} {repr(v)}\n"
            continue

        if isinstance(v, dict):
            rmsg += f"{msg}\n"
            rmsg += pprint_dict(
                v,
                color=color,
                capitalize=capitalize,
                indent=indent + indent_step,
                indent_step=indent_step,
                as_str=True,
            )
            continue

        elif isinstance(v, (list, tuple, set)):
            rmsg += f"{msg}\n"
            for item in v:
                if isinstance(item, dict):
                    rmsg += pprint_dict(
                        item,
                        color=color,
                        capitalize=capitalize,
                        indent=indent + indent_step,
                        indent_step=indent_step,
                        as_str=True,
                    )
                else:
                    rmsg += f"{' ' * (indent + indent_step)}- {item}\n"

        else:
            rmsg += f"{msg} {v}\n"

    if as_str:
        return rmsg
    else:
        _richprint(rmsg)
