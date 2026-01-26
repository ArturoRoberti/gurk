import sys
import traceback
from contextlib import contextmanager
from contextvars import ContextVar

from .logger import Logger
from .utils import LoggerSeverity

_allow_missing_logger = ContextVar("allow_missing_logger", default=False)
_current_logger = ContextVar("current_logger", default=None)


@contextmanager
def allow_missing_logger():
    """
    Context manager to allow operations without an active logger.
    """
    token = _allow_missing_logger.set(True)
    try:
        yield
    finally:
        _allow_missing_logger.reset(token)


def get_logger() -> Logger:
    """
    Get the currently active logger, if set.

    :return: The currently active logger
    :rtype: Logger
    :raises RuntimeError: If no logger is initialized and missing loggers are not allowed
    """
    logger = _current_logger.get()
    if logger is None:
        if not _allow_missing_logger.get():
            raise RuntimeError("Logger not initialized")
        else:
            return DummyLogger()

    return logger


class DummyLogger:
    """A dummy logger that replaces Logger functions when not initialized."""

    def __getattr__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __bool__(self):
        return False

    def __repr__(self):
        return "<Dummy Logger>"


class ActiveLogger:
    """Context manager to set an active logger globally."""

    def __init__(self, logger: Logger):
        self.logger = logger
        self._token = None

    def __enter__(self):
        # enter the logger itself
        self.logger.__enter__()

        # make it globally visible
        self._token = _current_logger.set(self.logger)

        return self.logger

    def __exit__(self, exc_type, exc, tb):
        # restore previous logger
        _current_logger.reset(self._token)

        # exit the logger itself
        self.logger.__exit__(exc_type, exc, tb)

        # no exception or SystemExit → just propagate
        if exc_type in (None, SystemExit):
            return False

        # Handle other exceptions
        if exc_type is KeyboardInterrupt:
            msg = "Process interrupted by user"
        else:
            traceback_str = "".join(
                traceback.format_exception(exc_type, exc, tb)
            )
            msg = f"An Exception occurred: {exc_type.__name__} - {exc}\n\n{traceback_str}"
        Logger.logrichprint(LoggerSeverity.FATAL, msg)
        sys.exit(1)
