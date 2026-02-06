# Overview
Plugins make up the core functionality of this package after [tasks](./tasks.md). Each plugin may define multiple tasks that can be run, and must define a way to run it (i.e. its tasks or tasks imported from other plugins). Plugins are defined via a plugin manifest file and use metadata defined in a `pyproject.toml` file. // for easy use in existing repositories.

# Plugin manifest
The plugin manifest is a YAML file named `gurk-manifest.yaml` located at the root of the plugin repository. It defines the plugin's metadata, tasks, and other configurations. The manifest has the following structure:
```yaml
imports:  # Optional
- <plugin-name-1>
  ...
- <plugin-repo-url-1>
- <plugin-repo-url-2>
  ...

tasks:  # Optional
  <task-name-1>: <TaskDict>
  <task-name-2>: <TaskDict>
  ...

options:  # Required
  <option-name-1>: <OptionDict>
  <option-name-2>: <OptionDict>
  ...
  default: <OptionDict>
  ...
```

## Imports
The `imports` section allows importing tasks from other plugins. Each entry can be either the name of a plugin already installed locally or a git repository URL of a remote plugin. Ideally, as `gurk` expands, all plugin imports (except for the core `gurk` plugin) should be specified as repository URLs only.

## Tasks
The optional `tasks` section defines the tasks provided by the plugin. Each task is defined using a `TaskDict`, as described in the [task documentation](./tasks.md).

If tasks are defined, each run option must reference at least one of the defined tasks.

## Options
The required `options` section defines the options in which the plugin can be run  (see the [knowledge base](../knowledge/run_tasks.md)).

Each option should only reference tasks defined in the `tasks` section of the manifest or tasks imported from other plugins. The `default` option is special/required and is used when no specific option is provided when running the plugin.

The structure of an `OptionDict` is as follows (all fields optional):
```yaml
<task-name>:
  config_file: <config_file>
  args: [<arg1>, <arg2>, ...]
  ...
```

Any arguments defined in the `args` field of enabled tasks will be passed to the task when run via the plugin option and removed from available CLI arguments for the task.

# Plugin metadata
Each plugin must also define its metadata in a `pyproject.toml` file located at the root of the plugin repository. The metadata should include the following fields:
```toml
[project]
name = "<name>"
version = "<version>"
description = "<description>"

[project.optional_dependencies]
gurk = ["dependency1", "dependency2", ...]
```

The `version` field should follow [semantic versioning](https://semver.org/) and is used to manage plugin versioning and upgrading.

The optional gurk dependencies are pip dependencies used by the plugin's python scripts and will be installed automatically to the plugin's venv when the plugin is pulled.

# Create a new plugin
To create a new plugin, follow these steps:
1. Create a template plugin directory in the current working directory using the `gurk template --name <plugin-name>` command. This will generate a basic plugin structure with the necessary files.
2. Create a git repository for the plugin or add its files to an existing one.
3. Edit the template plugin as required. You may use `gurk check <plugin-directory-path>` to validate the plugin during development.
4. Make the plugin available to others by making your repository public
5. If you want, create a pull request to add the plugin to the official plugin list in the `plugins/registry.yaml` file of this package. See the [contributing guidelines](../../.github/CONTRIBUTING.md).
