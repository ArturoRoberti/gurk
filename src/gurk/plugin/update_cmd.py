from dataclasses import dataclass, field

from gurk.plugin.utils import get_plugin_registries
from gurk.utils.common import PACKAGE_SRC_PATH
from gurk.utils.yaml import load_yaml


@dataclass(frozen=True)
class UpdateArgs:
    plugins: list[str] = field(
        metadata={
            "help": "Names of the plugins to update. If empty, update all local plugins."
        },
        default_factory=list,
    )


# TOOD: Allow '--remove' flag to also remove plugins that arein the plugin dirs but have no registry entry or vice-versa
# TODO: Update package plugins from submodule source (see .gitmodules - how to have access to that after upload to PyPI?). Maybe, instead of submodule, specify package plugins' git repo URL in a config file?
#       Update local plugins from their remote sources (git pull / download latest release)
def update_cmd(args: UpdateArgs):
    """Update all local plugins with remote sources"""
    # TODO: If no sources specified, update all plugins. If sources specified, only update those.
    if not args.plugins:
        # Get all local plugins to update if none specified
        pkg_registry_file, home_registry_file = get_plugin_registries()
        pkg_registry = load_yaml(pkg_registry_file)
        home_registry = load_yaml(home_registry_file)
        if not pkg_registry or not home_registry:
            # TODO: Use logger instead (fatal)
            return
        home_registry.update(pkg_registry)
        args.plugins = home_registry.keys()  # Prioritize home registry

    # Update package plugins
    # TODO

    # Update local plugins
    for plugin_path in (PACKAGE_SRC_PATH / "plugins").iterdir():
        if not plugin_path.is_dir():
            continue
        # Check if plugin has a remote source
        gurk_plugin_yaml_path = plugin_path / "gurk-plugin.yaml"
        if not gurk_plugin_yaml_path.exists():
            continue
