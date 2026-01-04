get_package_path() {
	: '
	Get the path to a package's resources using Python's importlib.resources.

	Args:
	  - package_name:   Name of the package.
	  - internal_path:  (Optional) Internal path within the package resources (default: '.').
	Outputs:
	  (stdout) Path to the package resources or internal path.
	  (stderr) Error messages in case of issues
	Returns:
	  0 if package path retrieved successfully, 1 otherwise
	'
	if [[ $# -lt 1 ]]; then
		echo "Error: missing required argument 'package_name'" >&2
		return 1
	fi

	local package_name="$1"
	local internal_path="${2:-.}"
	python3 -c "from importlib import resources; print(resources.files(\"${package_name}\") / \"${internal_path}\")"
}

PACKAGE_SRC_PATH=$(get_package_path "gurk")
PACKAGE_CONFIG_PATH="${PACKAGE_SRC_PATH}/config"

# Source helper scripts
PACKAGE_HELP_PATH="${PACKAGE_SRC_PATH}/scripts/bash/helpers"
for file in ${PACKAGE_HELP_PATH}/*.bash; do
	if [[ ! "$file" == "${PACKAGE_HELP_PATH}/helpers.bash" ]]; then
		source "$file"
	fi
done

# Source check scripts
for file in ${PACKAGE_SRC_PATH}/scripts/bash/*/checks.bash; do
	source "$file"
done

# Ensure this script is not run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	echo "This is a collection of helpers and cannot be run directly - source it instead" >&2
	exit 1
fi
