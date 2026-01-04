# Available user commands
## Core commands
- `install`: Install software
- `configure`: Configure software settings
- `uninstall`: Remove installed software

## Other commands
### `setup`
**Highly recommended** once before running any core command. Guides through initial manual setup steps:
- Configuring SSH keys for git (GitHub, GitLab, etc.) - some tasks may require cloning private repositories
- Disabling Secure Boot (e.g. for installing NVIDIA drivers)
> **NOTE**: You may also look up the general instructions for creating SSH keys [here](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key).
### `info`
Displays information about available tasks, configurations, and system status.

# Use core commands to run tasks
Tasks are the building blocks of gurk operations. Each core command provides a series of tasks. To see which tasks are available, run `gurk info --available-tasks`.

You can customize which tasks run and how via command-line flags and config files:

## Run core command with defaults
The simplest way to use gurk is to run a core command without extra flags. This uses the built-in default task selections. For example:
```bash
gurk install
```
This installs and configures a standard set of packages and settings. Note that some heavier tasks (e.g., CUDA, NVIDIA drivers, IsaacSim/Lab, ROS) are off by default, as not to bloat an average install.

## Run core command with specific tasks
To enable specific tasks or pass arguments you have two options:
- Use a config file (preferred for repeatability)
- Use command-line flags
The command-line flags complement the config file settings or override them, if they overlap.

### 1. Use a config file
You can specify which tasks to run and arguments to pass via a YAML config file of the form:
```yaml
<task1>:
    enabled: <true|false>
    args: [<arg1>, <arg2>, ...]
<task2>:
    enabled: <true|false>
<task3>:
    enabled: <true|false>
    args: [<arg1>, ...]
```
> **Note**: If no args are passed, default args (if any) are used. Also, task names should be prefixed by the core command name, e.g. `install-nvidia-driver`

You can also specify to enable all tasks or dependecies of specified tasks via the `enable-all: true` resp. `enable-dependencies: true` keys at the top level. For more information, use `gurk info --custom-config`.

Then, you can pass this config file via:
```bash
gurk install --config-file /path/to/config.yaml
```

### 2. Use command-line flags
You can specify which tasks to run and arguments to pass via the CLI by passing task names and optional colon-separated args of the form:
```bash
gurk install <task1>:<arg1>:<arg2> <task2> <task3>:<arg1> ...
```
> **NOTE**: Task names passed via the CLI should be without the core command prefix, e.g. `nvidia-driver`

For more information, use `gurk <command> --help` to see available flags for each core command.
