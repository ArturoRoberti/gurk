get_config_args() {
	: '
	Parses command-line arguments to extract system information and configuration directory.
	Populates global variables:
	  - SYSTEM_INFO:       Associative array of system information key-value pairs.
	  - CONFIG_FILE:       Path to the task configuration file.
	  - FORCE:             Boolean indicating if the --force flag was provided.
	  - REMAINING_ARGS:    Array of any additional arguments not parsed.

	Args:
	  - Configuration Args
	Outputs:
	  (stderr) Error messages in case of issues
	Returns:
	  0 if args parsed successfully, 1 otherwise
	'
	declare -gA SYSTEM_INFO=() # TODO: Use "simulate_hardware" entry
	declare -g CONFIG_FILE=""
	declare -g FORCE=false
	declare -g -a REMAINING_ARGS=()

	local system_info_raw=""

	# --- Parse arguments ---
	while [[ $# -gt 0 ]]; do
		case "$1" in
			--system-info)
				shift
				if [[ -z "$1" || "$1" == --* ]]; then
					echo "Error: --system-info requires a value" >&2
					return 1
				fi
				system_info_raw="$1"
				;;
			--config-file)
				shift
				if [[ -z "$1" || "$1" == --* ]]; then
					echo "Error: --config-file requires a value" >&2
					return 1
				fi
				CONFIG_FILE="$1"
				if [[ ! -f "$CONFIG_FILE" ]]; then
					echo "Error: Config file not found: $CONFIG_FILE" >&2
					return 1
				fi
				;;
			--force)
				FORCE=true
				;;
			*)
				REMAINING_ARGS+=("$1")
				;;
		esac
		shift
	done

	# --- Parse system-info string into associative array ---
	if [[ -n "$system_info_raw" ]]; then
		# Expect JSON-like input: '{"key": "value", "x": "y"}'
		local cleaned="${system_info_raw#\{}"
		cleaned="${cleaned%\}}"
		cleaned="${cleaned//\"/}"

		# Split into key:value pairs
		local pair key val
		IFS=',' read -ra pairs <<<"$cleaned"
		for pair in "${pairs[@]}"; do
			key="${pair%%:*}"
			val="${pair#*:}"
			key="$(echo "$key" | xargs)"
			val="$(echo "$val" | xargs)"
			SYSTEM_INFO["$key"]="$val"
		done
	fi
}

log_step() {
	: '
	Log a step message without advancing progress.

	Args:
	  - message:   Message to log.
	  - warning:   Whether or not this is a warning (default: false).
	Outputs:
	  Log messages indicating the current progress
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local message="$1"
	local warning="${2:-false}"

	local step_type="STEP_NO_PROGRESS"
	if [ "$warning" = true ]; then
		step_type+="_WARNING"
	fi
	echo -e "\n__${step_type}__: $message"
}

run_script_function() {
	: '
	Runs a script (Bash or Python), optionally invoking a specific function within it.

	Args:
	  - script:   Path to the script file.
	  - function: (Optional) Name of the function to invoke within the script. If omitted, the entire script is run.
	  - ...:      Additional arguments to pass to the script or function.
	Outputs:
	  Output from the script or function.
	Returns:
	  0 if executed successfully, 1 otherwise
	'
	local script="$1"
	local function="${2:-}"
	local ext="${script##*.}"
	case "${ext,,}" in
		bash)
			run_bash_script_function "$script" "$function" "${@:3}"
			;;
		py)
			run_python_script_function "$script" "$function" "${@:3}"
			;;
		*)
			echo "Unsupported script extension: $ext" >&2
			return 1
			;;
	esac
}

run_bash_script_function() {
	: '
	Runs a Bash script, optionally invoking a specific function within it.

	Args:
	  - script:   Path to the script file.
	  - function: (Optional) Name of the function to invoke within the script. If omitted, the entire script is run.
	  - ...:      Additional arguments to pass to the script or function.
	Outputs:
	  Output from the script or function.
	Returns:
	  0 if executed successfully, 1 otherwise
	'
	local script="$1"
	local function="${2:-}"

	# ASSUME the helper scripts are already sourced

	if [[ -n "$function" ]]; then
		# Source the script and call the function
		source "$script"
		"$function" "${@:3}"
	else
		# Run the script directly
		bash "$script" "${@:2}"
	fi
}

# TODO: Allow running with sudo too. How to differentiate "sudo" arg from other args?
run_python_script_function() {
	: '
	Runs a Python script, optionally invoking a specific function within it.

	Args:
	  - script:   Path to the script file.
	  - function: (Optional) Name of the function to invoke within the script. If omitted, the entire script is run.
	  - ...:      Additional arguments to pass to the script or function.
	Outputs:
	  Output from the script or function.
	Returns:
	  0 if executed successfully, 1 otherwise
	'
	if [[ $# -lt 1 ]]; then
		echo "Error: missing required argument 'script'" >&2
		return 1
	fi

	local script="$1"
	local func="${2:-}"
	shift

	python3 - "$@" <<-'EOF'
		import ast, sys

		script, func = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None
		args = sys.argv[3:]

		with open(script) as f:
			src = f.read()

		tree = ast.parse(src, filename=script)

		def find_main_body(tree):
			for n in tree.body:
				if isinstance(n, ast.If) and isinstance(n.test, ast.Compare):
					c = n.test
					if (isinstance(c.left, ast.Name) and c.left.id == "__name__"
						and isinstance(c.ops[0], ast.Eq)
						and isinstance(c.comparators[0], ast.Constant)
						and c.comparators[0].value == "__main__"):
						return n.body
			return None

		def run_nodes(nodes, ns=None):
			code = compile(ast.Module(nodes, []), script, "exec")
			exec(code, ns or {"__name__": "__main__"})

		if func:
			fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == func), None)
			if not fn:
				sys.exit(f"Function '{func}' not found in {script}")
			ns = {}
			run_nodes([fn], ns)
			res = ns[func](*args)
			sys.exit(res if isinstance(res, int) else 0)
		else:
			body = find_main_body(tree)
			if not body:
				sys.exit(f"No '__main__' block found in {script}")
			run_nodes(body)
	EOF
}
