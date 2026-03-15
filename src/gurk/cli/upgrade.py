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

from pathlib import Path

from gurk.lib.context import GurkContext, GurkLock, Logger, get_registries
from gurk.lib.context.registry import (
    get_plugin_registration,
    is_plugin_registered,
)
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    is_plugin_installed,
    upgrade_plugin,
)
from gurk.lib.shared.remotes import extract_url, is_git_installed, is_git_repo


class UpgradeNamespace(DefaultNamespace):
    plugins: list[str]
    exclude: list[str] | None


def main(argv, prog, description):
    parser = GurkArgumentParser[UpgradeNamespace](
        prog=prog, description=description
    )
    group = parser.add_required_group()
    group.add_argument(
        "plugins",
        type=str,
        nargs="*",
        help="Names of the registered plugins to upgrade. If empty, upgrade all local plugins",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        type=str,
        nargs="+",
        help="PluginSpecifications (name or remote) to exclude from upgrade when upgrading all plugins",
    )
    args = parser.parse_args(argv)

    # Execute with writing to plugins
    with (
        GurkLock(),
        GurkContext(
            logger=Logger(
                verbose=args.verbose,
                non_interactive=args.non_interactive,
                description="Upgrading plugins",
            ),
            writable=True,
        ) as ctx,
    ):
        # Check that git is installed
        if not is_git_installed():
            ctx.logger.fatal(
                "Git is not installed or not available in PATH."
                "Please install it via 'sudo apt install git'"
            )

        # Parse plugin specifications to upgrade
        if args.plugins:
            plugins = args.plugins
            for plugin in plugins:
                # Only allow plugin names
                if Path(plugin).exists() or is_git_repo(plugin):
                    ctx.logger.error(
                        f"Invalid plugin specification '{plugin}' given "
                        f"for upgrade. Only plugin names are allowed."
                    )
                    plugins.remove(plugin)
        else:
            # Get all local plugins to upgrade if none specified
            combined_registry = get_registries(
                public=True, private=True, combine=True
            )
            plugins = combined_registry.keys()  # All plugin names

        # Check 'exclude' plugins if specified
        normalized_exclude = set()
        for exclude in args.exclude or []:
            # Don't allow local paths
            if Path(exclude).exists():
                ctx.logger.error(
                    f"Invalid plugin specification '{exclude}' given for exclusion. "
                    f"Only plugin names or remotes are allowed. Skipping..."
                )
                continue

            # Check that the plugin to exclude exists
            if not is_plugin_installed(exclude, require_venv=False):
                ctx.logger.warning(
                    f"Excluded plugin '{exclude}' is not validly installed. Ignoring..."
                )
                continue
            else:
                normalized_exclude.add(extract_url(exclude))

        for plugin in plugins:
            # Check if plugin is registered
            if not is_plugin_registered(
                plugin,
                public=True,
                private=True,
                require_local=False,
            ):
                ctx.logger.error(
                    f"Plugin '{plugin}' is not registered. Skipping upgrade..."
                )
                continue

            # Get available plugin data from registration
            plugin_registration = get_plugin_registration(
                plugin,
                public=True,
                private=True,
                require_local=False,
            )
            plugin_name, plugin_entry = next(iter(plugin_registration.items()))
            plugin_local = (
                (
                    plugin_entry["local"].as_posix()
                    if isinstance(plugin_entry["local"], Path)
                    else plugin_entry["local"]
                ),
            )
            plugin_remote = plugin_entry["remote"]

            # Skip local-only plugins
            if not plugin_remote:
                ctx.logger.error(
                    f"Plugin '{plugin}' is local-only and has no remote. Skipping upgrade..."
                )
                continue

            # Exclude specified plugins
            if normalized_exclude & {
                plugin_name,
                plugin_local,
                extract_url(plugin_remote),
            }:
                ctx.logger.debug(f"Excluding plugin '{plugin}' from upgrade.")
                continue

            # Upgrade plugin from remotes
            upgrade_plugin(plugin)

        ctx.logger.done("Plugin upgrades complete.")
