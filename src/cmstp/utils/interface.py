import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import List, Optional, Union

from rich import print as richprint

from cmstp.utils.command import CommandKind
from cmstp.utils.common import (
    PACKAGE_BASH_HELPERS_PATH,
    PIPX_PYTHON_PATH,
    FilePath,
)


def run_script_function(
    script: FilePath,
    function: Optional[str] = None,
    args: List[str] = [],
    run: bool = True,
    capture_output: bool = False,
    sudo: bool = False,
) -> Union[str, subprocess.CompletedProcess]:
    """
    Build a wrapper script string for the specified command kind and optionally execute it.

    :param script: The path to the script to source or execute.
    :type script: FilePath
    :param function: The function within the script to call. If None, the script is executed directly.
    :type function: Optional[str]
    :param args: Arguments to pass to the function or script
    :type args: List[str]
    :param run: If True, executes the script. Otherwise, returns the string.
    :type run: bool
    :param capture_output: If True, captures the output of the script. Ignored if run=False.
    :type capture_output: bool
    :param sudo: If True, runs python scripts with sudo privileges.
    :type sudo: bool
    :return: The generated script string (if run=False)
    :rtype: str | CompletedProcess
    """
    if not Path(script).exists():
        raise FileNotFoundError(f"Script file not found: {script}")
    # TODO: Add check for function existence. Make util for this somewhere and use both here and in scheduler

    kind = CommandKind.from_script(script)
    if kind == CommandKind.BASH:
        return _run_bash_script_function(
            script, function, args, run, capture_output
        )
    elif kind == CommandKind.PYTHON:
        return _run_python_script_function(
            script, function, args, run, capture_output, sudo
        )
    else:
        raise ValueError(
            f"Unsupported script type: {kind} (supported: {CommandKind.BASH.name}, {CommandKind.PYTHON.name})"
        )


def _run_bash_script_function(
    script: FilePath,
    function: Optional[str],
    args: List[str],
    run: bool,
    capture_output: bool,
) -> Union[str, subprocess.CompletedProcess]:
    """
    Build a bash wrapper script string and optionally execute it.

    :param script: The path to the script to source or execute.
    :type script: FilePath
    :param function: The function within the script to call. If None, the script is executed directly.
    :type function: Optional[str]
    :param args: Arguments to pass to the function or script
    :type args: List[str]
    :param run: If True, executes the script. Otherwise, returns the string.
    :type run: bool
    :param capture_output: If True, captures the output of the script. Ignored if run=False.
    :type capture_output: bool
    :return: The generated script string (if run=False)
    :rtype: str | CompletedProcess
    """
    # Source pipx venv and helpers
    sourcing = dedent(
        f"""\
        source {PIPX_PYTHON_PATH.parent / 'activate'}
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


def _run_python_script_function(
    script: FilePath,
    function: Optional[str],
    args: List[str],
    run: bool,
    capture_output: bool,
    sudo: bool,
) -> Union[str, subprocess.CompletedProcess]:
    """
    Build a Python wrapper script string and optionally execute it.

    :param script: The path to the script to source or execute.
    :type script: FilePath
    :param function: The function within the script to call. If None, the script is executed directly.
    :type function: Optional[str]
    :param args: Arguments to pass to the function or script
    :type args: List[str]
    :param run: If True, executes the script. Otherwise, returns the string.
    :type run: bool
    :param capture_output: If True, captures the output of the script. Ignored if run=False.
    :type capture_output: bool
    :param sudo: If True, runs python scripts with sudo privileges.
    :type sudo: bool
    :return: The generated script string (if run=False)
    :rtype: str | CompletedProcess
    """
    if function:
        # Import the module dynamically and call the function
        wrapper_src = dedent(
            f"""\
            import importlib.util, sys
            p = {repr(str(script))}
            spec = importlib.util.spec_from_file_location('_run_mod', p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            func = getattr(mod, {repr(function)})
            res = func({', '.join(repr(arg) for arg in args)})
            if isinstance(res, int):
                sys.exit(res)
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
        return subprocess.run(
            [*sudo_prefix, CommandKind.PYTHON.exe, "-c", wrapper_src],
            capture_output=capture_output,
            text=True,
        )

    return wrapper_src


def bash_check(check_name: str) -> subprocess.CompletedProcess:
    """
    Run a (helper) check function

    :param check_name: Name of the check function to run
    :type check_name: str
    :return: CompletedProcess result of the check
    :rtype: CompletedProcess
    """
    # Create a mock bash file (used only as a placeholder)
    with NamedTemporaryFile(
        mode="w", suffix=".bash", delete=False
    ) as tmp_file:
        tmp_file.write("#!/usr/bin/env bash\n")
        tmp_file_path = Path(tmp_file.name)

    try:
        # Try running the helper function
        return run_script_function(
            script=tmp_file_path,
            function=check_name,
            run=True,
            capture_output=True,
        )
    except Exception as e:
        # Return a failed CompletedProcess instead of None
        return subprocess.CompletedProcess(
            args=[str(tmp_file_path), check_name],
            returncode=1,
            stdout=b"",
            stderr=str(e).encode(),
        )
    finally:
        # Always clean up
        tmp_file_path.unlink(missing_ok=True)


def revert_sudo_permissions(path: FilePath) -> None:
    """
    Revert sudo permissions on the specified path using bash helper.

    :param path: Path to revert permissions on
    :type path: FilePath
    """
    run_script_function(
        script=PACKAGE_BASH_HELPERS_PATH,
        function="revert_sudo_permissions",
        args=[str(path)],
        run=True,
    )


def promt_bool(message: str) -> bool:
    """
    Prompt the user for a yes/no response.

    :param message: The prompt message.
    :type message: str
    :return: True if the user responds with 'y', False for 'n'.
    :rtype: bool
    """
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ["y", "n"]:
            return response == "y"
        else:
            richprint("Invalid input. Please enter 'y' or 'n'")
