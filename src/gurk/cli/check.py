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

from gurk.lib.context import GurkContext, Logger
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    check_local_plugin,
)


class CheckNamespace(DefaultNamespace):
    paths: list[str]


def main(argv, prog, description):
    parser = GurkArgumentParser[CheckNamespace](
        prog=prog, description=description
    )
    group = parser.add_required_group()
    group.add_argument(
        "paths",
        type=str,
        nargs="+",
        help="Local paths of custom plugins to check",
    )
    args = parser.parse_args(argv)

    # Execute without writing to plugins
    with GurkContext(
        logger=Logger(
            verbose=args.verbose,
            non_interactive=args.non_interactive,
            description="Checking plugins",
        ),
        writable=False,
    ) as ctx:
        for source in args.paths:
            if not check_local_plugin(source, True):
                ctx.logger.fatal(f"Plugin at '{source}' is invalid.")
            else:
                ctx.logger.info(f"Plugin at '{source}' is valid.")

        ctx.logger.done("Plugin checks complete.")
