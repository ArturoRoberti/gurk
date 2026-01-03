# Task structure
Any task has the following structure in the default config file (`src/cmstp/config/default.yaml`):
```yaml
<task-name>:
	description: <Task description>
	script: <script_name>.py
	function: <function_name>
	config_file: <config_file>
	depends_on: [<dependency1>, <dependency2>, ...]
	privileged: <true|false>
	supercedes: [<task1>, <task2>, ...]
	args:
		allowed: [<allowed_arg1>, <allowed_arg2>, ...]
		default: [<default_arg1>, <default_arg2>, ...]
```
> **NOTE**: Only the `description`, `script`, and `function` fields are mandatory. All other fields are optional, resp. need to be added in the config file using the `defaults` anchor helper defined at the top of the file. Also note that the `script` and `config_file` fields should only contain the file name, not the full path (which is inferred from the task name and script extension).

**Example:**
```yaml
my-mock-task:
	<<: *defaults
	description: My mock task description
	script: my_mock_script.py
	function: my_mock_function
```

Further information on the task structure can be found at the top of the default config file itself (`src/cmstp/config/default.yaml`) or by using
```bash
cmstp info --default-config
```

# Add a new task
1. **Edit `src/cmstp/config/default.yaml`:** Add a new task entry, setting all fields as described above.
2. **Implement the script/function:**
	 - Add the function in the appropriate script (or create one) under `src/cmstp/scripts/<language>/<command>/<script>.<ext>`
	 - If the script is meant to be run fully, add an entrypoint instead (see existings scripts for reference) and set the `function` field to `null`.
3. **(Optional) Add a config file:** Place a config file in `src/cmstp/config/<command>/` if the task uses one.

# Add a new task field
To add a new field, you need to:
1. Update the `TASK_PROPERTIES_*` variables in `src/cmstp/utils/tasks.py` to include the new field and its default type(s).
2. Update the task processor to handle/check the new field accordingly
3. If the variable propagates to the scheduler, edit the `ResolvedTask` dataclass in `src/cmstp/utils/tasks.py`, set the value at the end of the task processor's `__post__init__` method, and update the scheduler accordingly
