# Overview
Tasks, which can run arbitrary scripts, are the core functionality of Gurk and can be run by themselves or plugin configurations called "options" using the `gurk run` command.

# Running tasks directly
To run a task directly, use the following command:
```bash
gurk run [-v|--verbose] [--non-interactive] <plugin>/<task-subname> [<args>]
```
- `<plugin>`: The specification of the plugin the task belongs to. This can be a plugin name (e.g. `my-plugin`), a local path to a plugin (e.g. `dir/my-plugin`), or a remote git repository URL (e.g. `git@github.com:ArturoRoberti/example_gurk_plugin.git`).
- `<task-subname>`: The subname of the task to run, whose full name is `<plugin-name>/<task-subname>`.
- `<args>`: Optional arguments to pass to the task. The available arguments can be determined via `gurk run <plugin>/<task-subname> --help` (or `gurk help --task <task-name>`). Note that dependency tasks are automatically enabled, thus their arguments are also available.

# Running tasks via plugin options
To run tasks via a plugin option, use the following command:
```bash
gurk run [-v|--verbose] [--non-interactive] <plugin>[:<option-name>] [<args>]
```
- `<plugin>`: The specification of the plugin the option belongs to. This can be a plugin name (e.g. `my-plugin`), a local path to a plugin (e.g. `dir/my-plugin`), or a remote git repository URL (e.g. `git@github.com:ArturoRoberti/example_gurk_plugin.git`).
- `<option-name>`: (Optional) The name of the option defined in the plugin's manifest to run. If not provided, the `default` option will be used.
- `<args>`: Optional arguments to pass to the tasks enabled in the selected option. The available arguments can be determined via `gurk run <plugin-name> --help` (or `gurk help --plugin <plugin-name>`). Note that dependency tasks are automatically enabled, thus their arguments are also available.

If you wish to save an options configuration, create a mock plugin with a manifest file defining the desired option, import it via `gurk pull <mock-plugin-repo-url>` and run it via `gurk run <mock-plugin-name>[:<option-name>]` (or directly use `gurk run <mock-plugin-repo-url>[:<option-name>]`). A plugin option must have the following structure in the manifest:
```yaml
<option-name>:
  <task-name-1>:
    config_file: <config_file>
    args: [<arg1>, <arg2>, ...]
  <task-name-2>: {}
  ...
```
- `<task-name>`: The full name of the task to enable/disable in the option. Again, dependency tasks are automatically enabled in their default configuration.
- `config_file`: (Optional) Path to a config file to use for the task instead of the default one.
- `args`: (Optional) List of arguments to pass as CLI arguments to the task when run via the option.

We can **highly recommend** storing your own plugin in a remote git repository, so that you can easily set up any new system with your preferred settings and packages. This is what is done in the [example gurk plugin](https://github.com/ArturoRoberti/example_gurk_plugin.git).
