import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

from cmstp.core.logger import Logger, LoggerSeverity
from cmstp.utils.system_info import SystemInfo


def get_config_args(
    args=sys.argv[1:],
) -> Tuple[SystemInfo, Path, List[str]]:
    """Parse command-line arguments and return system info, config info, and remaining args."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--system-info", type=str, default=None)
    # parser.add_argument("--simulate-hardware", action="store_true")  # Now included in system info
    # parser.add_argument(
    #     "--config-directory",
    #     type=Path,
    #     default=None
    # )
    parser.add_argument("--config-file", type=Path, default=None)
    args, remaining = parser.parse_known_args(args)

    # System info
    system_info = {}
    if args.system_info:
        try:
            # Parse JSON input
            system_info = json.loads(args.system_info)
            if not isinstance(system_info, dict):
                raise ValueError("The value for --system-info must be a dict.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for --system-info: {e}")

    # Config file
    if args.config_file is not None and not args.config_file.exists():
        Logger.logrichprint(
            LoggerSeverity.FATAL, f"Config file not found: {args.config_file}"
        )
        raise FileNotFoundError

    return system_info, args.config_file, remaining


# Example function usage
def _example_function(*args):
    system_info, config_info, remaining = get_config_args(args)

    # Use argparse for the rest
    parser = argparse.ArgumentParser()
    parser.add_argument("--foo")
    parser.add_argument("--bar")
    remaining_args = parser.parse_args(remaining)

    foo_arg = remaining_args.foo


# Example main usage
if __name__ == "__main__":
    system_info, config_info, remaining = get_config_args()

    # Use argparse for the rest
    parser = argparse.ArgumentParser()
    parser.add_argument("--foo")
    parser.add_argument("--bar")
    remaining_args = parser.parse_args(remaining)

    foo_arg = remaining_args.foo
