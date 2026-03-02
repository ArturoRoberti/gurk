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
from dataclasses import dataclass, field
from pathlib import Path
from venv import EnvBuilder

from gurk.lib.context import get_plugin_directories
from gurk.lib.core.plugins import get_remote_plugin_version, get_venv_dir
from gurk.lib.shared.configs import dump_yaml, load_yaml
from gurk.lib.shared.plugins import PluginRegistry, PluginRegistryEntry
from gurk.lib.utils import PACKAGE_SRC_PATH, InputValidationError, typecheck

from ...utils import PYTEST_PLUGIN_NAME, PytestInputException, RegistryKind
from .constants import is_registration_valid
from .local_plugin import PreparedLocalPlugin


@dataclass
class PreparedPluginRegistration:
    """Context manager to create and clean up a plugin registration for testing."""

    # fmt: off
    entry: PluginRegistryEntry | None = field()
    kind:                RegistryKind = field(default=RegistryKind.HOME)
    venv_exists:                 bool = field(default=False)
    # fmt: on

    @typecheck
    def _validate_inputs(
        self,
        entry: PluginRegistryEntry | None,
        kind: RegistryKind,
        venv_exists: bool,
    ) -> None:
        # Most of the validation is handled by '@typecheck'
        # ...

        # Validate that the registration entry has no empty string values
        if entry is not None and any(
            isinstance(v, str) and v.strip() == "" for v in entry.values()
        ):
            raise InputValidationError(
                "Plugin registry entry cannot have empty string values."
            )

    def __post_init__(self):
        # Validate input types
        try:
            self._validate_inputs(
                entry=self.entry, kind=self.kind, venv_exists=self.venv_exists
            )
        except InputValidationError as e:
            raise PytestInputException(str(e)) from None

        # Validate that the combination of parameters is valid
        if not is_registration_valid(self.entry, self.kind, self.venv_exists):
            raise PytestInputException(
                f"Invalid combination of parameters for PreparedPluginRegistration: "
                f"entry={self.entry}, kind={self.kind}, venv_exists={self.venv_exists}"
            )

        # Resolve the local path (if any)
        if self.entry is not None and self.entry["local"] is not None:
            plugin_directory: Path = get_plugin_directories(
                home_registry=self.kind == RegistryKind.HOME,
                package_registry=self.kind == RegistryKind.PACKAGE,
            )[0]
            self.entry["local"] = (
                plugin_directory / self.entry["local"]
            ).as_posix()

    @property
    def is_registered(self) -> bool:
        return self.entry is not None

    @property
    def is_installed(self) -> bool:
        return self.is_registered and self.entry["local"] is not None

    def __enter__(self):
        self.prepare()

        return self

    def __exit__(self, exc_type, exc, tb):
        # Remove any installation
        self.entry = None
        self.venv_exists = False
        self.prepare()

        # Propagate exceptions
        return False

    def prepare(self):
        """
        Prepare the test environment for plugin registration and installation.
        """
        # Clean up plugin directories to ensure a clean slate for tests
        for plugin_dir in get_plugin_directories():
            for child in plugin_dir.iterdir():
                if child.is_dir() and child.name == PYTEST_PLUGIN_NAME:
                    # Remove any existing pytest plugin (should not be necessary)
                    shutil.rmtree(child)
                elif child.name == "registry.yaml":
                    # Change the registry as requested
                    registry: PluginRegistry = load_yaml(child)
                    if self.is_registered and (
                        child.is_relative_to(PACKAGE_SRC_PATH)
                        == (self.kind == RegistryKind.PACKAGE)
                    ):
                        registry[PYTEST_PLUGIN_NAME] = self.entry
                    else:
                        registry.pop(PYTEST_PLUGIN_NAME, None)
                    dump_yaml(registry, child)

        # Install the plugin if specified
        if self.is_installed:
            # Extract specified remote version
            if self.entry["remote"]:
                specified_version = get_remote_plugin_version(
                    self.entry["remote"]
                )
            else:
                specified_version = None

            # Extract kwargs for PreparedLocalPlugin
            if specified_version is None:
                kwargs = {}
            else:
                kwargs = {"version": specified_version}

            with PreparedLocalPlugin(**kwargs) as plugin_path:
                # Install the plugin manually
                dest = self.entry["local"]
                if Path(dest).exists():
                    shutil.rmtree(dest)
                Path(plugin_path).rename(dest)

        # Create a virtual environment for the plugin if specified
        venv_dir = get_venv_dir(PYTEST_PLUGIN_NAME)
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
        if self.venv_exists:
            EnvBuilder().create(venv_dir)


def prepared_plugin_registration_id(
    param: tuple[PluginRegistryEntry | None, RegistryKind, bool]
) -> str:
    """
    Generate a test identification string for plugin registration scenarios.

    :param param: A tuple containing plugin registration parameters
    :type param: tuple[PluginRegistryEntry | None, RegistryKind, bool]
    :return: A formatted string identifier combining kind, entry type, and venv status
    :rtype: str
    """
    entry, kind, venv_exists = param
    if entry is None:
        kind_part = ""
        entry_part = "unregistered"
        venv_part = ""
    else:
        kind_part = f"{kind.name}-"
        entry_part = "entry("
        if entry["local"]:
            entry_part += "local"
        if entry["remote"]:
            if entry["local"]:
                entry_part += ","
            entry_part += "remote"
        entry_part += ")-"
        venv_part = ("" if venv_exists else "no_") + "venv"
    return f"{kind_part}{entry_part}{venv_part}"
