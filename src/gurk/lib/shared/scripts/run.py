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
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import Any, Literal, overload

from gurk.lib.shared.scripts import check_script_function
from gurk.lib.utils import (
    PACKAGE_BASH_HELPERS_PATH,
    PIPX_PYTHON_PATH,
    ListOrTuple,
    PathLike,
    typecheck,
)

from .command import CommandKind


@overload
def run_script_function(
    run: Literal[True],
    *args: Any,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    ...


@overload
def run_script_function(
    run: Literal[False],
    *args: Any,
    **kwargs: Any,
) -> str:
    ...


@typecheck
def run_script_function(
    script: PathLike,
    function: None | str = None,
    args: ListOrTuple[str] | None = None,
    *,
    run: bool = True,
    capture_output: bool = False,
    venv: PathLike | None = None,
    sudo: bool = False,
    check: bool = True,
) -> str | subprocess.CompletedProcess[str]:
    """
    Build a wrapper script string for the specified command kind and optionally execute it.

    :param script: The path to the script to source or execute.
    :type script: PathLike
    :param function: The function within the script to call. If None, the script is executed directly.
    :type function: None | str
    :param args: Arguments to pass to the function or script
    :type args: ListOrTuple[str] | None
    :param run: If True, executes the script. Otherwise, returns the string.
    :type run: bool
    :param capture_output: If True, captures the output of the script. Ignored if run=False.
    :type capture_output: bool
    :param venv: Optional path to a virtual environment to use when running the script. If one, the current venv is used.
    :type venv: PathLike | None
    :param sudo: If True, runs python scripts with sudo privileges.
    :type sudo: bool
    :param check: If True, checks if the script and function exist before running. Usually set to False if e.g. the function is sourced from another script (e.g. with a bash helper).
    :type check: bool
    :return: The generated script string (if run=False)
    :rtype: str if 'run' else subprocess.CompletedProcess[str]
    :raises FileNotFoundError: If the script or function do not exist and check=True, or if the specified venv does not exist.
    :raises ValueError: If the script extension is not supported.
    """
    if args is None:
        args = []

    if check:
        # Check script and function exist and are valid
        errors = check_script_function(script, function)
        if errors:
            raise FileNotFoundError("\n".join(errors))

    # Check venv existence
    if venv and not venv.exists():
        raise FileNotFoundError(f"Virtual environment not found: {venv}")

    # Run respective command
    if CommandKind.from_script(script) == CommandKind.PYTHON:
        return _run_python_script_function(
            script, function, args, run, capture_output, venv, sudo
        )
    else:
        return _run_bash_script_function(
            script, function, args, run, capture_output, venv
        )


@typecheck
def _run_bash_script_function(
    script: PathLike,
    function: None | str,
    args: ListOrTuple[str],
    run: bool,
    capture_output: bool,
    venv: PathLike | None,
) -> str | subprocess.CompletedProcess[str]:
    """
    Build a bash wrapper script string and optionally execute it.

    :param script: The path to the script to source or execute.
    :type script: PathLike
    :param function: The function within the script to call. If None, the script is executed directly.
    :type function: None | str
    :param args: Arguments to pass to the function or script
    :type args: ListOrTuple[str]
    :param run: If True, executes the script. Otherwise, returns the string.
    :type run: bool
    :param capture_output: If True, captures the output of the script. Ignored if run=False.
    :type capture_output: bool
    :param venv: Optional path to a virtual environment to use when running the script. If one, the current venv is used.
    :type venv: PathLike | None
    :return: The generated script string (if run=False)
    :rtype: str | CompletedProcess
    """
    # Source pipx venv and helpers
    venv = Path(venv or PIPX_PYTHON_PATH.parents[1])
    sourcing = dedent(
        f"""\
        source {venv / 'bin' / 'activate'}
        source {PACKAGE_BASH_HELPERS_PATH}
    """
    )

    # Build script body
    if function:
        # Simply source and call function
        body = sourcing + dedent(
            f"""\
            source {script}
            {function} {' '.join(repr(arg) for arg in args)}
        """
        )
    else:
        # Create temporary sourcing file for usage with BASH_ENV
        sourcing_file = NamedTemporaryFile(
            mode="w", suffix=".bash", prefix="sourcing_", delete=False
        )
        sourcing_file.write(sourcing)
        sourcing_file.flush()
        sourcing_file.close()

        # Run the script with BASH_ENV set
        body = dedent(
            f"""\
            export BASH_ENV='{sourcing_file.name}'
            {CommandKind.BASH.exe} {script} {' '.join(repr(arg) for arg in args)}
        """
        )

    # (Run) Full bash script
    wrapper_src = (
        dedent(
            """\
        #!/usr/bin/env bash
        set -euo pipefail
    """
        )
        + body
    )
    if run:
        return subprocess.run(
            [CommandKind.BASH.exe, "-c", wrapper_src],
            capture_output=capture_output,
            text=True,
        )

    return wrapper_src


@typecheck
def _run_python_script_function(
    script: PathLike,
    function: None | str,
    args: ListOrTuple[str],
    run: bool,
    capture_output: bool,
    venv: PathLike | None,
    sudo: bool,
) -> str | subprocess.CompletedProcess[str]:
    """
    Build a Python wrapper script string and optionally execute it.

    :param script: The path to the script to source or execute.
    :type script: PathLike
    :param function: The function within the script to call. If None, the script is executed directly.
    :type function: None | str
    :param args: Arguments to pass to the function or script
    :type args: ListOrTuple[str]
    :param run: If True, executes the script. Otherwise, returns the string.
    :type run: bool
    :param capture_output: If True, captures the output of the script. Ignored if run=False.
    :type capture_output: bool
    :param venv: Optional path to a virtual environment to use when running the script. If one, the current venv is used.
    :type venv: PathLike | None
    :param sudo: If True, runs python scripts with sudo privileges.
    :type sudo: bool
    :return: The generated script string (if run=False)
    :rtype: str | CompletedProcess
    """
    if function:
        # Import the module dynamically and call the function
        wrapper_src = dedent(
            f"""\
            import importlib.util
            p = {repr(str(script))}
            spec = importlib.util.spec_from_file_location('_run_mod', p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            func = getattr(mod, {repr(function)})
            res = func({', '.join(repr(arg) for arg in args)})
            if isinstance(res, int):
                raise SystemExit(res)
        """
        )
    else:
        # Just execute the script directly
        wrapper_src = dedent(
            f"""\
            import sys
            from pathlib import Path
            script = Path({repr(str(script))})
            sys.path.insert(0, str(script.parent))
            sys.argv = ['__main__', {', '.join(repr(arg) for arg in args)}]
            with open(script, 'rb') as f:
                code = compile(f.read(), script, 'exec')
                exec(code, {{'__name__': '__main__'}})
        """
        )

    if run:
        sudo_prefix = ["sudo", "-E"] if sudo else []
        exe = (
            CommandKind.PYTHON.exe
            if not venv
            else str(Path(venv) / "bin" / "python3")
        )
        return subprocess.run(
            [*sudo_prefix, exe, "-c", wrapper_src],
            capture_output=capture_output,
            text=True,
        )

    return wrapper_src


@typecheck
def revert_sudo_permissions(path: PathLike) -> None:
    """
    Revert sudo permissions on the specified path using bash helper.

    :param path: Path to revert permissions on
    :type path: PathLike
    """
    run_script_function(
        script=PACKAGE_BASH_HELPERS_PATH,
        function="revert_sudo_permissions",
        args=[str(path)],
        run=True,
        check=False,
    )
