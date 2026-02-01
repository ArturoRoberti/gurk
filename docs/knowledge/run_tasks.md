# Overview
Tasks, which can run arbitrary scripts, are the core functionality of Gurk and can be run by themselves or plugin configurations called "options" using the `gurk run` command.

# Running tasks directly
To run a task directly, use the following command:
```bash
gurk run [-v|--verbose] [--non-interactive] --task <task-name> [<args>]
```
- `<task-name>`: The full name of the task to run, i.e. `<plugin-name>/<task-subname>`.
- `<args>`: Optional arguments to pass to the task. The available arguments can be determined via `gurk run --task <task-name> --help` (or `gurk help --task <task-name>`). Note that dependency tasks are automatically enabled, thus their arguments are also available.

# Running tasks via plugin options
To run tasks via a plugin option, use the following command:
```bash
gurk run [-v|--verbose] [--non-interactive] --plugin <plugin-name>[=<option-name>] [<args>]
```
- `<plugin-name>`: The name of the plugin to run.
- `<option-name>`: (Optional) The name of the option defined in the plugin's manifest to run. If not provided, the `default` option will be used.
- `<args>`: Optional arguments to pass to the tasks enabled in the selected option. The available arguments can be determined via `gurk run --plugin <plugin-name> --help` (or `gurk help --plugin <plugin-name>`). Note that dependency tasks are automatically enabled, thus their arguments are also available.

If you wish to save an options configuration, create a mock plugin with a manifest file defining the desired option, import it via `gurk pull` and run it via `gurk run --plugin <mock-plugin-name>[=<option-name>]`. A plugin option must have the following structure in the manifest:
```yaml
<option-name>:
  <task-name-1>:
    enabled: true
    config_file: <config_file>
    args: [<arg1>, <arg2>, ...]
  <task-name-2>:
  ...
```
- `<task-name>`: The name of the task to enable/disable in the option. Again, dependency tasks are automatically enabled in their default configuration.
- `enabled`: Whether to enable (`true`) or disable (`false`) the task when running the option.
- `config_file`: (Optional) Path to a config file to use for the task instead of the default one.
- `args`: (Optional) List of arguments to pass as CLI arguments to the task when run via the option.

We can **highly recommend** storing your own plugin in a remote git repository, so that you can easily set up any new system with your preferred settings and packages. This is what is done in the [example gurk plugin](https://github.com/ArturoRoberti/example_gurk_plugin.git).
