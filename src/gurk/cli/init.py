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

from gurk.lib.context import GurkContext, Logger, get_registries
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    create_plugin_venv,
    get_venv_gurk_version,
    install_plugin,
    is_plugin_installed,
    remove_venv,
    venv_exists,
)
from gurk.lib.utils import GURK_VERSION, PACKAGE_NAME


def main(argv, prog, description):
    parser = GurkArgumentParser[DefaultNamespace](
        prog=prog, description=description
    )
    args = parser.parse_args(argv)

    # Execute with writing to plugins
    with GurkContext(
        logger=Logger(
            verbose=args.verbose,
            non_interactive=args.non_interactive,
            description=f"Initializing {PACKAGE_NAME}",
        ),
        writable=True,
    ) as ctx:
        combined_registry = get_registries(
            home_registry=True, package_registry=True, combine=True
        )
        for plugin_name, plugin_entry in combined_registry.items():
            # Skip gurk core plugin
            if plugin_name == "gurk":
                continue

            # Remove plugin venv (if any) with different gurk version
            if (
                venv_exists(plugin_name)
                and get_venv_gurk_version(plugin_name) != GURK_VERSION
            ):
                ctx.logger.debug(
                    f"Removing existing virtual environment for plugin '{plugin_name}' to ensure it is re-created with the current gurk version."
                )
                if not remove_venv(plugin_name):
                    ctx.logger.error(
                        f"Failed to remove existing virtual environment for plugin '{plugin_name}'."
                    )
                    return False

            # Check if plugin is already validly installed
            if not is_plugin_installed(plugin_name, require_venv=False):
                if plugin_entry.get("remote"):
                    # Pull plugin (and remove any existing invalid plugin) if not installed
                    source = plugin_entry["remote"]
                    ctx.logger.debug(
                        f"Plugin '{plugin_name}' is not installed. Pulling from remote '{source}'..."
                    )
                    if not install_plugin(source, reinstall=True):
                        ctx.logger.error(
                            f"Failed to pull plugin '{plugin_name}' from '{source}'."
                        )
                        continue
                else:
                    ctx.logger.warning(
                        f"Local plugin '{plugin_name}' is not validly installed. Please remove it manually."
                    )
                    continue
            else:
                ctx.logger.debug(
                    f"Plugin '{plugin_name}' is already installed - skipping installation."
                )

            # CHECK: Plugin should now be installed
            if not is_plugin_installed(plugin_name, require_venv=False):
                ctx.logger.error(
                    f"Unexpected: Plugin '{plugin_name}' is "
                    "still not installed. Skipping venv creation."
                )
                continue

            # Create plugin venv
            if not venv_exists(plugin_name):
                if not create_plugin_venv(plugin_name):
                    ctx.logger.error(
                        f"Failed to create virtual environment for plugin '{plugin_name}'",
                    )
                    continue
            else:
                ctx.logger.debug(
                    f"Plugin '{plugin_name}' virtual environment already exists - skipping creation."
                )

        ctx.logger.done("Initialization complete.")
