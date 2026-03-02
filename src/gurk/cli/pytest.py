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
from tempfile import TemporaryDirectory

from gurk.lib.context import GurkContext, Logger, get_plugin_directories


@dataclass
class SafeFileHandler:
    registries: dict[str, Path] = field(init=False, default_factory=dict)

    def __enter__(self):
        # Store original registry states for cleanup
        for plugin_dir in get_plugin_directories():
            with TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
            shutil.copytree(plugin_dir, tmp_dir, symlinks=True)
            self.registries[plugin_dir.as_posix()] = tmp_dir

    def __exit__(self, exc_type, exc, tb):
        # Restore original registries
        for plugin_dir, tmp_dir in self.registries.items():
            if Path(plugin_dir).exists():
                shutil.rmtree(plugin_dir)
            shutil.copytree(tmp_dir, plugin_dir, symlinks=True)

        # Propagate exceptions
        return False


def main(argv):
    with GurkContext(
        logger=Logger(verbose=False, non_interactive=False, store_logs=False),
        writable=False,
    ) as ctx:
        # Check that pytest is installed
        try:
            import pytest
        except ImportError:
            ctx.logger.fatal(
                "'pytest' is not installed. Please install this package with the "
                "'dev' extras to use this command via: 'pipx install -e .[dev]'"
            )

    # Run pytests with a safe file handler to prevent any modifications to plugin registries during testing
    with (
        SafeFileHandler(),
        GurkContext(
            logger=None,
            writable=False,
        ) as ctx,
    ):
        # Run pytests
        raise SystemExit(pytest.main(argv))
