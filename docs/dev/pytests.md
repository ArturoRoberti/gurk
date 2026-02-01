# Overview
Apart from the user commands, this package currently also provides the `pytest` command for running tests. You can test the validity of package configs and scripts via
```bash
gurk pytest tests/tasks.py --tasks TASK1[,TASK2,TASK3,...]
```
> **NOTE:** For now, when not used on a GitHub Actions runner, this command only checks task configs and scripts for syntax errors and importability, but does not actually run the tasks.

When adding a new task, its behavior may be different on GitHub CI runners w.r.t. local runs. To handle this, special runner-specific tasks may be defined using the `RUNNER_SPECIFIC_TASKS` variable in `src/gurk/utils/tasks.py`.
> **NOTE**: This should not be a long-term solution, but rather a temporary workaround until proper mocking or simulation of hardware-specific features is implemented in tests.
