from packaging.version import InvalidVersion, Version

from .types import PytestInputException


def bump_patch(version_str: str) -> str:
    """
    Bump the patch version of a version string (e.g., "1.0.0" -> "1.0.1").

    :param version_str: The version string to bump
    :type version_str: str
    :return: The bumped version string
    :rtype: str
    """
    # Get release components (major, minor, patch)
    try:
        v = Version(version_str)
    except InvalidVersion:
        raise PytestInputException(
            f"Invalid version string '{version_str}' provided for bumping."
        )

    # Return new version string with incremented patch
    return f"{v.major}.{v.minor}.{v.micro + 1}"
