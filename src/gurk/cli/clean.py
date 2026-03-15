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

import shutil
from pathlib import Path

from gurk.lib.context import Logger, get_logger
from gurk.lib.core.plugins import DefaultNamespace, GurkArgumentParser
from gurk.lib.utils.constants import (
    PACKAGE_CACHE_PATH,
    PACKAGE_CONFIG_PATH,
    PACKAGE_DATA_PATH,
    PACKAGE_LOG_PATH,
    PACKAGE_NAME,
)


class CleanNamespace(DefaultNamespace):
    purge: bool


def _remove_dir(path: Path, label: str) -> None:
    """Helper function to remove a directory and log the action."""
    # Get logger
    logger = get_logger()

    # Remove directory (if any)
    if path.exists():
        logger.info(f"Removing {label} directory: {path}")
        shutil.rmtree(path)
    else:
        logger.debug(f"Skipping {label} directory (not found): {path}")


def main(argv, prog, description):
    parser = GurkArgumentParser[CleanNamespace](
        prog=prog, description=description
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Remove data and configs in addition to cache and logs.",
    )
    args = parser.parse_args(argv)

    with Logger(
        verbose=args.verbose,
        non_interactive=args.non_interactive,
        description=f"Cleaning {PACKAGE_NAME} directories",
    ) as logger:
        _remove_dir(PACKAGE_LOG_PATH, "log")
        _remove_dir(PACKAGE_CACHE_PATH, "cache")

        if args.purge:
            _remove_dir(PACKAGE_DATA_PATH, "data")
            _remove_dir(PACKAGE_CONFIG_PATH, "config")

        logger.done(f"Cleaned {PACKAGE_NAME} directories successfully!")
