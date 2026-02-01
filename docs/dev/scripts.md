# Logger and Steps
The progress bar is updated via `STEP` statements in both Bash and Python scripts. There are three types of `STEP` statements:

| Print Format                   | Purpose                                                               | Example Implementation                                                                                           |
|--------------------------------|-----------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `__STEP__`                     | Updates progress bar text and progress                                | `# (STEP) Description`<br>Comment is replaced by `__STEP__` print in scheduler, see [scheduler.md](scheduler.md) |
| `__STEP_NO_PROGRESS__`         | Updates progress bar text only                                        | **Bash:** `log_step "Description"`<br>**Python:** `Logger.step("Description")`                                   |
| `__STEP_NO_PROGRESS_WARNING__` | Updates progress bar text only, marks task as warning/partial success | **Bash:** `log_step "Description" true`<br>**Python:** `Logger.step("Description", warning=True)`                |

**Example (Python):**
```python
from gurk.core.logger import Logger
# (STEP) Some step with progress
Logger.step("Some step without progress")
Logger.step("Some step with warning", warning=True)
```

**Example (Bash):**
```bash
# (STEP) Some step with progress
log_step "Some step without progress"
log_step "Some step with warning" true
```

# Helpers and checks
Script helpers include functions for file processing, logging steps, and more. Check functions verify if a task is already completed and should be used to either skip tasks at the start or verify its success at the end.

All bash script helpers in `lib/helpers/bash/` are sourced automatically by the scheduler before running any script or function. On the other hand, all python script helpers must be imported explicitly. The helper `run_script_function` (Bash & Python) may be used to run a check function or helper from the other language.

To add a new helper, add it to any file in `lib/helpers/bash/` (Bash) resp. anywhere in this package (ideally in `lib/helpers/python/`) (Python).

# Argument passing
Each script can get access to the args passed by the scheduler via the `parse_task_args` helper function. This returns a system info dictionary, the task's config file path, the `--force` flag (True/False), and any remaining task-specific arguments from its plugin definition.

## Python
```python
from gurk import parse_task_args
...
def my_task_function(*args: list[str]) -> None:
    """Task function description."""
    # Parse task args
    task_args = parse_task_args(args)
    ...

    # (pathlib.Path) Config file
    config_file = task_args.config_file

    # (bool) Force flag
    force = task_args.force

    # (dict[str, str]) System info
    system_info = task_args.system_info

    # (Any) Remaining parsed task args (NOTE: --some-arg -> some_arg)
    some_arg = task_args.some_arg
    ...
```

## Bash
```bash
# Helper is automatically sourced by scheduler
...
my_task_function() {
    : "
    Task function description.
    "
    # Parse task args
	parse_task_args "$@"

    # (str) Config file
    local config_file="${CONFIG_FILE}"

    # (bool) Force flag
    local force="${FORCE}"

    # (associative array) System info
    for key in "${!SYSTEM_INFO[@]}"; do
        echo "Key: $key, Value: ${SYSTEM_INFO[$key]}"
    done
    local version="${SYSTEM_INFO[version]}"

    # (Any) Remaining parsed task args (NOTE: --some-arg -> SOME_ARG)
    SOME_ARG="${SOME_ARG}"
    ...
}
