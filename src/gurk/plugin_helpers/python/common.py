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

import subprocess
from pathlib import Path
from typing import Literal

from gurk.lib.shared.scripts import run_script_function
from gurk.lib.utils import PACKAGE_BASH_HELPERS_PATH, typecheck

from .interface import log_step

PasswdField = Literal[
    "username",
    "uid",
    "gid",
    "gecos",
    "home",
    "shell",
]


@typecheck
def getent_passwd(
    user: str | int,
    field: PasswdField,
) -> str:
    """
    Retrieve specific fields from the system's user database for a given user.

    :param user: The username or user ID to look up
    :type user: str | int
    :param field: The field to retrieve from the user's passwd entry
    :type field: PasswdField
    :return: The requested field from the user's passwd entry
    :rtype: str
    :raises ValueError: If an invalid field is specified or the user is not found
    """
    if field not in PasswdField.__args__:
        raise ValueError(f"Invalid field: {field!r}")

    # Retrieve the passwd entry using getent
    try:
        output = subprocess.check_output(
            ["getent", "passwd", str(user)],
            text=True,
        )
    except subprocess.CalledProcessError:
        raise ValueError(f"User {user!r} not found")

    # Parse the output and extract the requested field
    parts = output.strip().split(":")
    INDEXES = {
        "username": 0,
        "uid": 2,
        "gid": 3,
        "gecos": 4,
        "home": 5,
        "shell": 6,
    }
    return parts[INDEXES[field]]


@typecheck
def add_alias(command: str) -> None:
    """
    Add an alias to ~/.bashrc if it doesn't already exist.

    :param command: The alias command to add
    :type command: str
    """
    alias_cmd = f"alias {command}"
    run_script_function(
        script=PACKAGE_BASH_HELPERS_PATH,
        function="write_marked",
        args=[alias_cmd, str(Path.home() / ".bashrc")],
        run=True,
        check=False,
    )
    log_step(f"Successfully added alias: {alias_cmd}")
