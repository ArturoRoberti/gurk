# Overview
The scheduler is responsible for:
- [Scheduling parallelized task execution](#task-scheduling)
- [Pre-processing scripts for execution](#pre-processing)
- [Tracking task progress](#progress-tracking-via-pty)

# Task scheduling
The scheduler receives a list of resolved tasks, each with a list of dependencies. It starts any given task when all its dependencies have completed successfully, and runs tasks in parallel threads where possible.

# Pre-processing
Before executing a task, the scheduler preprocesses its script to:
- Inject progress-tracking `STEP` statements at the task's function or entrypoint
- Remove any other `STEP` statements to avoid counting issues
- Handle `sudo` prompts via a `sudo -A` (askpass) wrapper
- Source the pipx virtual environment and any helper scripts (Bash only)

# Progress tracking via PTY
The scheduler uses PTY (pseudo-TTY) to spawn subprocesses, allowing it to capture task output at runtime to detect progress statements and update the progress bar accordingly.
> **NOTE**: This comes at the cost of not separating stdout and stderr streams.
