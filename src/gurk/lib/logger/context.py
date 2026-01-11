import sys
import traceback
from contextvars import ContextVar

from .logger import Logger, LoggerSeverity

_current_logger = ContextVar("current_logger", default=None)


def get_logger() -> Logger:
    """Get the currently active logger, if set."""
    logger = _current_logger.get()
    if logger is None:
        raise RuntimeError("Logger not initialized")
    return logger


class ActiveLogger:
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
