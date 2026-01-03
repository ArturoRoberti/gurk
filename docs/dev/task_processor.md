# Overview
The task processor is implemented is responsible for:
1. Loading the default config and overlays custom config and CLI tasks
2. Validating allowed arguments for each task
3. Applying `--enable-all` and `--enable-dependencies` flags
4. Disabling tasks not matching the current core command
5. Filling missing custom fields with defaults
6. Resolving config file paths and dependency/supercedes graphs

> **NOTE**: The `--force` flag is always added to the list of allowed arguments for each task, allowing tasks to handle it as needed.
