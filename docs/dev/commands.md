# Available developer commands
Apart from the user commands, this package currently also provides the `pytest` command for running tests. You can test the validity of package configs and scripts via
```bash
gurk pytest tests/configs.py
gurk pytest tests/scripts.py
```

You can also test individual tasks via either using the gurk core commands as any user would or using
```bash
gurk pytest tests/tasks.py --tasks TASK1[,TASK2,TASK3,...]
```

When adding a new task, its behavior may be different on GitHub CI runners w.r.t. local runs. To handle this, special runner-specific tasks may be defined using the `RUNNER_SPECIFIC_TASKS` variable in `src/gurk/utils/tasks.py`.
> **NOTE**: This should not be a long-term solution, but rather a temporary workaround until proper mocking or simulation of hardware-specific features is implemented in tests.

# Add a new command
- **`CORE` Command:** Edit the `CORE_COMMANDS` variable in `src/gurk/cli/utils.py`. Furthermore, add a new section for this command in the default config file (`src/gurk/config/default.yaml`), following the structure of existing commands.

- **`Developer` Command:** Please add it similar to existing ones in `main.py` - remember to add it to the developer command group via:
    ```python
    main.commands[<command_name>].category = "Developer Commands"
    ```

- **`Other` Command:** Please also add it similar to existing ones in `main.py` and create a main file for it in `src/gurk/cli/`.

- You can add own argparsers to each subcommand. In that case, please pass `prog` and `description` to the `ArgumentParser` constructor for consistent help messages, similar to how it is done for core commands.
