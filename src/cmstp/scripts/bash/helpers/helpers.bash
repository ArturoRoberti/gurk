get_package_path() {
  if [[ $# -lt 1 ]]; then
    echo "Error: missing required argument 'package_name'" >&2
    return 1
  fi

  local package_name="$1"
  local internal_path="${2:-.}"
  python3 -c "from importlib import resources; print(resources.files(\"${package_name}\") / \"${internal_path}\")"
}

PACKAGE_SRC_PATH=$(get_package_path "cmstp")
PACKAGE_CONFIG_PATH="${PACKAGE_SRC_PATH}/config"

# Source helper scripts
PACKAGE_HELP_PATH="${PACKAGE_SRC_PATH}/scripts/bash/helpers"
for file in ${PACKAGE_HELP_PATH}/*.bash; do
  if [[ ! "$file" == "${PACKAGE_HELP_PATH}/helpers.bash" ]]; then
    source "$file"
  fi
done

# Source check scripts
source "${PACKAGE_SRC_PATH}/scripts/bash/configurations/checks.bash"
source "${PACKAGE_SRC_PATH}/scripts/bash/installations/checks.bash"

# Ensure this script is not run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "This is a collection of helpers and cannot be run directly - source it instead" >&2
  exit 1
fi
