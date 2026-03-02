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

import os
import platform
import subprocess

import distro

from .types import SystemInfo


def _get_architecture() -> str:
    """
    Retrieve the system architecture using dpkg.

    :return: System architecture string
    :rtype: str
    :raises RuntimeError: If the dpkg command fails
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
    :raises RuntimeError: If the manufacturer information cannot be retrieved
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
    :raises RuntimeError: If the OS is unsupported or required info cannot be retrieved
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
    system_info["arch"] = _get_architecture()
    ## manufacturer
    system_info["manufacturer"] = get_manufacturer()

    return system_info
