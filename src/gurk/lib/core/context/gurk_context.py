from contextlib import ExitStack

from .logger import DummyLogger, Logger, get_logger
from .registry_manager import RegistryManager


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
