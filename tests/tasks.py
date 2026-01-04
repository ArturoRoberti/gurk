import pytest

from cmstp.cli import core

from .utils import _get_sudo_askpass, padded_print, print_task_outputs


def test_task(task: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Parametrized test for any task. Used mainly in github actions to test affected tasks only."""

    # Disable/Replace prompts
    monkeypatch.setattr(core, "get_sudo_askpass", _get_sudo_askpass)
    monkeypatch.setattr(
        core.CoreCliProcessor, "prompt_setup", lambda self: None
    )

    # Run task and capture task results
    captured = []
    with pytest.raises(SystemExit) as e:
        core.main(
            argv=[task, "--enable-dependencies", "-v"],
            prog="",
            description="",
            cmd=task.split("-")[0],
            _captured=captured,
        )
    assert (
        e.value.code == 0
    ), f"Core exited with non-zero code for task '{task}'"

    successful_tasks = [task for task in captured if task[2]]
    failed_tasks = [task for task in captured if not task[2]]

    # Print successful task outputs
    if successful_tasks:
        padded_print(f"Successful tasks ({len(successful_tasks)})")
        print_task_outputs(successful_tasks)
    else:
        padded_print("No successful tasks", stderr=True)

    # Print failed task outputs
    if failed_tasks:
        padded_print(f"Failed tasks ({len(failed_tasks)})", stderr=True)
        print_task_outputs(failed_tasks, stderr=True)
    else:
        padded_print("No failed tasks")

    assert not failed_tasks, "There should be no failed tasks"
