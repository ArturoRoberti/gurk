# flake8: noqa
from importlib.metadata import version

from .lib.core.context import Logger, LoggerSeverity
from .lib.helpers import *
from .lib.utils import *

__version__ = version("gurk")
