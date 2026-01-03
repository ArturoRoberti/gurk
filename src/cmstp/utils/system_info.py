import os
import platform
import subprocess
from typing import Optional, TypedDict

import distro


class SystemInfo(TypedDict):
    """Detailed information about the host operating system."""

    # fmt: off
    type:              str
    kernel:            str
    name:              Optional[str]
    codename:          Optional[str]
    version:           Optional[str]
    arch:              str
    simulate_hardware: bool
    manufacturer:      str
    # fmt: on


def get_architecture() -> str:
    """
    Retrieve the system architecture using dpkg.

    :return: System architecture string
    :rtype: str
    """
    result = subprocess.run(
        ["dpkg", "--print-architecture"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to retrieve architecture info via dpkg: {result.stderr.strip()}"
        )
    else:
        return result.stdout.strip().lower()


def get_manufacturer() -> str:
    """
    Retrieve the system manufacturer using dmidecode.

    :return: System manufacturer string
    :rtype: str
    """
    try:
        with open("/sys/class/dmi/id/sys_vendor") as f:
            manufacturer = f.read().strip()
            if manufacturer:
                return manufacturer.lower()
            else:
                raise RuntimeError("Manufacturer info is empty")
    except Exception as e:
        raise RuntimeError(
            f"Failed to retrieve manufacturer info via sysfs: {e}"
        )


def get_system_info() -> SystemInfo:
    """
    Retrieve detailed information about the host system.

    :return: System information dictionary
    :rtype: SystemInfo
    """
    system_info = SystemInfo()
    # OS-independent values
    ## linux, darwin, etc.
    system_info["type"] = platform.system().lower()
    ## x86_64, aarch64, etc.
    system_info["kernel"] = platform.machine()
    ## Simulate Hardware (e.g. GPU) in CI
    system_info["simulate_hardware"] = os.getenv("GITHUB_ACTIONS") == "true"

    # Linux-specific values
    if system_info["type"] != "linux":
        # Unsupported OS
        raise RuntimeError(f"Unsupported OS: {system_info['type']}")
    ## ubuntu, debian, etc.
    system_info["name"] = distro.id().lower()
    ## focal, jammy, buster, bullseye, etc.
    system_info["codename"] = distro.codename().lower()
    ## 20.04, 22.04, etc.
    system_info["version"] = distro.version()
    ## amd64, arm64, etc.
    system_info["arch"] = get_architecture()
    ## manufacturer
    system_info["manufacturer"] = get_manufacturer()

    return system_info
