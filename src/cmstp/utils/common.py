import os
import shutil
import sys
from importlib import resources
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import Optional, Union

from cmstp.utils.patterns import PatternCollection

PACKAGE_SRC_PATH = Path(resources.files("cmstp")).expanduser().resolve()
PACKAGE_CONFIG_PATH = PACKAGE_SRC_PATH / "config"
PACKAGE_TESTS_PATH = PACKAGE_SRC_PATH.parents[1] / "tests"
PACKAGE_BASH_HELPERS_PATH = (
    PACKAGE_SRC_PATH / "scripts" / "bash" / "helpers" / "helpers.bash"
)
PIPX_PYTHON_PATH = Path(sys.executable)

FilePath = Union[Path, str]


def generate_random_path(
    suffix: Optional[str] = None,
    prefix: Optional[str] = None,
    create: bool = False,
) -> Path:
    if suffix is not None and suffix.startswith("."):
        # File
        fd, path = mkstemp(suffix, prefix)
        os.close(fd)
        if not create:
            os.remove(path)
    else:
        # Directory
        path = mkdtemp(suffix, prefix)
        if not create:
            shutil.rmtree(path)

    return Path(path)


def is_simple_path(path: FilePath) -> bool:
    invalid = '<>:"|?*@'
    return not any(ch in invalid for ch in str(path))


def resolve_package_path(raw_script: FilePath) -> Optional[FilePath]:
    """
    Resolve paths that may refer to package resources. Package paths are in the format:
        "package://<package-name>/relative/path/inside/package"
    The input type (should be Path or str) is preserved in the output.
    """
    # Return wrong types as-is
    if not isinstance(raw_script, (Path, str)):
        return raw_script

    # Resolve package paths
    match = PatternCollection.PATH.patterns["package"].match(str(raw_script))
    if match:
        pkg_name, rel_path = match.groups()
        try:
            resolved_path = Path(resources.files(pkg_name)) / rel_path
        except ModuleNotFoundError:
            return None
    else:
        # NOTE: We use 'os' and no built-in 'Path' method to retain '<type>://' multiple slashes
        resolved_path = os.path.expanduser(str(raw_script))

    # Return same type as input
    if isinstance(raw_script, Path):
        return Path(resolved_path)
    else:  # str
        return str(resolved_path)
