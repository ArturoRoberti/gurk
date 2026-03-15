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

try:
    from gurk.lib.context import GurkContext, Logger, get_registries
    from gurk.lib.core.plugins import upgrade_plugin
except ImportError:
    raise ImportError(
        "The gurk package needs to be installed to run this script."
    )

if __name__ == "__main__":
    with GurkContext(
        logger=Logger(verbose=True, non_interactive=True, store_logs=False),
        writable=True,
    ):
        if not all(
            upgrade_plugin(name, require_local=False)
            for name, entry in get_registries(
                public=False, private=True
            ).items()
            if entry["remote"]
        ):
            raise SystemExit(1)
