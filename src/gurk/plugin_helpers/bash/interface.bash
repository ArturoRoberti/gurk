log_step() {
	: "
	Log a step message without advancing progress. Only to be used from within tasks.

	Args:
	  - message:   Message to log.
	  - warning:   Whether or not this is a warning (default: false).
	Outputs:
	  Log messages indicating the current progress
	Returns:
	  0 (unless an unexpected error occurs)
	"
	local message="$1"
	local warning="${2:-false}"

	local step_type="STEP_NO_PROGRESS"
	if [ "$warning" = true ]; then
		step_type+="_WARNING"
	fi
	echo -e "\n__${step_type}__: $message"
}

run_script_function() {
	: "
	Runs a script (Bash or Python), optionally invoking a specific function within it.
		NOTE: This mirrors the Python function of the same name in 'lib/utils/interface.py', with bash limitations considered.

	Args:
	  - script:   Path to the script file.
	  - function: (Optional) Name of the function to invoke within the script. If omitted, the entire script is run.
	  - sudo:     (Optional) Whether to run the script with sudo privileges (default: false).
	  - ...:      (Optional) Additional arguments to pass to the script or function.
	Outputs:
	  Output from the script or function.
	Returns:
	  0 if executed successfully, 1 otherwise
	"
	local script="$1"
	local function="${2:-}"
	local venv="${3:-}"
	local sudo="${4:-false}"
	local args=("${@:5}")
	local ext="${script##*.}"
	case "${ext,,}" in
		bash)
			run_bash_script_function "$script" "$function" "$venv" "${args[@]}"
			;;
		py)
			run_python_script_function "$script" "$function" "$venv" "$sudo" "${args[@]}"
			;;
		*)
			echo "Unsupported script extension: $ext" >&2
			return 1
			;;
	esac
}

run_bash_script_function() {
	: "
	Runs a Bash script, optionally invoking a specific function within it.

	Args:
	  - script:   Path to the script file.
	  - function: (Optional) Name of the function to invoke within the script. If omitted, the entire script is run.
	  - venv:     (Optional) Path to a virtual environment to use when running the script. If one, the current venv is used.
	  - ...:      (Optional) Additional arguments to pass to the script or function.
	Outputs:
	  Output from the script or function.
	Returns:
	  0 if executed successfully, 1 otherwise
	"
	local script="$1"
	local function="${2:-}"
	local venv="${3:-}"
	local args=("${@:4}")

	if [[ -n "$venv" ]]; then
		# Activate the virtual environment
		source "$venv/bin/activate"
	fi

	if [[ -n "$function" ]]; then
		# Source the script and call the function
		source "$script" "$function" "${args[@]}"
	else
		# Run the script directly
		bash "$script" "${args[@]}"
	fi
}

run_python_script_function() {
	: "
	Runs a Python script, optionally invoking a specific function within it.

	Args:
	  - script:   Path to the script file.
	  - function: (Optional) Name of the function to invoke within the script. If omitted, the entire script is run.
	  - venv:     (Optional) Path to a virtual environment to use when running the script. If one, the current venv is used.
	  - sudo:     (Optional) Whether to run the script with sudo privileges (default: false).
	  - ...:      (Optional) Additional arguments to pass to the script or function.
	Outputs:
	  Output from the script or function.
	Returns:
	  0 if executed successfully, 1 otherwise
	"
	if [[ $# -lt 1 ]]; then
		echo "Error: missing required argument 'script'" >&2
		return 1
	fi

	local script="$1"
	local func="${2:-}"
	local venv="${3:-}"
	local sudo="${4:-false}"
	local args=("${@:5}")

	local py_exe=""
	if [[ -n "$venv" ]]; then
		py_exe="$venv/bin/python3"
	else
		py_exe="python3"
	fi

	if [[ "$sudo" == true ]]; then
		py_exe="sudo $py_exe"
	fi

	$py_exe - "${args[@]}" <<-'EOF'
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
				raise SystemExit(f"Function '{func}' not found in {script}")
			ns = {}
			run_nodes([fn], ns)
			res = ns[func](*args)
			raise SystemExit(res if isinstance(res, int) else 0)
		else:
			body = find_main_body(tree)
			if not body:
				raise SystemExit(f"No '__main__' block found in {script}")
			run_nodes(body)
	EOF
}
