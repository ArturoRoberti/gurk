import shutil
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

from gurk.lib.context import GurkContext, Logger, get_plugin_directories
from gurk.lib.core.runner import check_askpass


@dataclass
class SafeFileHandler:
    registries: dict[str, Path] = field(init=False, default_factory=dict)

    def __enter__(self):
        # Store original registry states for cleanup
        for plugin_dir in get_plugin_directories(
            home_registry=True, package_registry=True
        ):
            with TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
            shutil.copytree(plugin_dir, tmp_dir)
            self.registries[plugin_dir.as_posix()] = tmp_dir

    def __exit__(self, exc_type, exc, tb):
        # Restore original registries
        for plugin_dir, tmp_dir in self.registries.items():
            if Path(plugin_dir).exists():
                shutil.rmtree(plugin_dir)
            shutil.copytree(tmp_dir, plugin_dir)

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

        # Check 'SUDO_ASKPASS'
        if any("test_tasks.py" in arg for arg in argv) and not check_askpass():
            ctx.logger.warning(
                "'SUDO_ASKPASS' is not properly set. Plugin files will be "
                "statically checked for errors, but no tasks will be run."
            )

    with SafeFileHandler(), GurkContext(
        logger=None,
        writable=False,
    ) as ctx:
        # Run pytests
        raise SystemExit(pytest.main(argv))
