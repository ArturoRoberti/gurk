# Overview
The processor is responsible for:
1. Enabling dependencies of enabled tasks
2. Preparing the task argparser to parse CLI task arguments
3. Adding the gurk prepatation task

> **NOTE**: The `--force` flag is always added to the list of allowed arguments for each task, allowing tasks to handle it as needed.
