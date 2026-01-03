# Logger and Steps
The progress bar is updated via `STEP` statements in both Bash and Python scripts. There are three types of `STEP` statements:

| Print Format                   | Purpose                                                               | Example Implementation                                                                                           |
|--------------------------------|-----------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `__STEP__`                     | Updates progress bar text and progress                                | `# (STEP) Description`<br>Comment is replaced by `__STEP__` print in scheduler, see [scheduler.md](scheduler.md) |
| `__STEP_NO_PROGRESS__`         | Updates progress bar text only                                        | **Bash:** `log_step "Description"`<br>**Python:** `Logger.step("Description")`                                   |
| `__STEP_NO_PROGRESS_WARNING__` | Updates progress bar text only, marks task as warning/partial success | **Bash:** `log_step "Description" true`<br>**Python:** `Logger.step("Description", warning=True)`                |

**Example (Python):**
```python
from cmstp.core.logger import Logger
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

All bash script helpers in `src/cmstp/scripts/bash/helpers/` are sourced automatically by the scheduler before running any script or function. On the other hand, all python script helpers must be imported explicitly. Similarly, all bash check functions in `src/cmstp/scripts/bash/<command>/checks.bash` are also sourced automatically and python check functions must be imported explicitly.

The helper `run_script_function` (Bash & Python) may be used to run a check function or helper from the other language.

To add a new helper, add it to any file in `src/cmstp/scripts/bash/helpers/` (Bash) resp. anywhere in this package (ideally in `src/cmstp/scripts/python/helpers/`) (Python). To add a new check function, add it to `src/cmstp/scripts/<language>/<command>/checks.py`.

# Variable passing
Each script can get access to variables passed by the scheduler via the `get_config_args` helper function. This returns a system info dictionary, the task's config file path, the `--force` flag (True/False), and any remaining arguments as a list:

| Argument       | Python                              | Bash                                              |
|----------------|-------------------------------------|---------------------------------------------------|
| System Info    | `Dict[str, str]` First return value | (Associative array) `SYSTEM_INFO` global variable |
| Config File    | `Path` Second return value          | (str) `CONFIG_FILE` global variable               |
| `--force` Flag | `bool` Third return value           | (bool) `FORCE` global variable                    |
| Remaining Args | `List[str]` Fourth return value     | (array) `REMAINING_ARGS` global variable          |
