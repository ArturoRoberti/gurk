some_function() {
	: "
    This is a descriptive docstring for some_function.

	Args:
	  - Arg1: Description of the first argument.
	  - Arg2: Description of the second argument.
	  ...
	Outputs:
	  Description of the outputs produced by the function.
	Returns:
	  Description of the return values or status codes.
	"
	# Parse task args (if needed)
	parse_task_args "$@"

	echo "This is a sample function in some_script.bash"
}
