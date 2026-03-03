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

from contextlib import ExitStack

from .logger import DummyLogger, Logger, get_logger
from .registry import RegistryManager


class GurkContext:
    """
    Context manager for Gurk that handles setup and teardown of resources like the plugin registry.
    """

    def __init__(self, *, logger: Logger | None, writable: bool):
        self._logger = logger or DummyLogger()
        self._registry_manager = RegistryManager(writable=writable)
        self._stack = ExitStack()

    def __enter__(self):
        self._stack.enter_context(self._logger)
        self._stack.enter_context(self._registry_manager)
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._stack.__exit__(exc_type, exc, tb)

    @property
    def logger(self) -> Logger:
        return get_logger()
