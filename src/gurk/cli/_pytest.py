from gurk.lib.core.context import GurkContext, Logger
from gurk.lib.utils.runner import check_askpass


def main(argv):
    with GurkContext(logger=Logger(False, False, None), writable=False) as ctx:
        # Check that pytest is installed
        try:
            import pytest
        except ImportError:
            ctx.logger.fatal(
                "'pytest' is not installed. Please install this package with the "
                "'dev' extras to use this command via: 'pipx install -e .[dev]'"
            )

        # Check 'SUDO_ASKPASS'
        if not check_askpass():
            ctx.logger.warning(
                "'SUDO_ASKPASS' is not properly set. Plugin files will be "
                "statically checked for errors, but no tasks will be run."
            )

    # Run pytests
    raise SystemExit(pytest.main(argv))
