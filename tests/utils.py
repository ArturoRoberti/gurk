import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from gurk.utils.common import stream_print


def _get_sudo_askpass() -> str:
    """
    Create a temporary sudo askpass script that provides no password.

    :return: Path to the temporary askpass script
    :rtype: str
    """
    with NamedTemporaryFile(mode="w", delete=False) as askpass_file:
        askpass_file.write("#!/bin/sh\necho ''\n")
        askpass_path = askpass_file.name
    os.chmod(askpass_path, 0o700)
    return askpass_path


def print_task_outputs(
    tasks: list[tuple[str, str, bool]], stderr: bool = False
) -> None:
    """
    Print the contents of task output files.

    :param tasks: List of tuples containing task name, output file path, and success status
    :type tasks: list[tuple[str, str, bool]]
    :param stderr: Whether to print to stderr instead of stdout
    :type stderr: bool
    """
    for task in tasks:
        # Print task name
        stream_print(f"\n{task[0]}:", stderr)

        # Print the logfile (if it exists - would not be the case in e.g. a skipped task)
        if task[1] is not None and Path(task[1]).is_file():
            with open(task[1], "r") as f:
                stream_print(f.read(), stderr)


def padded_print(
    text: str, total_length: int = 128, stderr: bool = False
) -> None:
    """
    Print text padded with "=" signs to center it within a specified total length.

    :param text: Text to be printed
    :type text: str
    :param total_length: Total length of the printed line including padding
    :type total_length: int
    :param stderr: Whether to print to stderr instead of stdout
    :type stderr: bool
    """
    # Top bar
    stream_print("\n" + "=" * total_length, stderr)

    # Calculate how many "=" signs are needed in the middle
    #   Subtract 2 for extra spaces
    remaining_length = total_length - len(text) - 2
    if remaining_length < 0:
        stream_print(f"{text}", stderr)
    else:
        left_pad = remaining_length // 2
        right_pad = remaining_length - left_pad
        stream_print(f"{'=' * left_pad} {text} {'=' * right_pad}", stderr)

    # Bottom bar
    stream_print("=" * total_length + "\n", stderr)
