# Task structure
Any task definitiom should have the following structure in its plugin manifest:
```yaml
<task-name>:
	description: <Task description>
	script: <script_name>.py
	function: <function_name>
	config_file: <config_file>
	depends_on: [<dependency1>, <dependency2>, ...]
	privileged: <true|false>
	supercedes: [<task1>, <task2>, ...]
	args: <ArgsDict>
```
> **NOTE**: Only the `description`, `script`, and `function` fields are mandatory Also note that the `script` and `config_file` fields should be specified relative to the plugin repo root (i.e. the same as the plugin manifest).
> **NOTE**: For the `args` field, see the [args documentation](./args.md).

For existing examples of task definitions, use `gurk help --task <task>` to see the task details (e.g. `gurk help --task gurk/install-apt-packages`).

# Add a new task field
To add a new field, you need to:
1. Update the `[Resolved]CustomTaskDict` classes in `lib/utils/tasks.py` to include the new field and its default type(s).
2. If the field has complex validation requirements, edit the `check_local_plugin` function in `lib/utils/plugins.py` to include the new field validation.
3. Update the processor and/or scheduler to use the new field.
