# Source helper scripts
for file in $(dirname "${BASH_SOURCE[0]}")/*.bash; do
	if [[ ! "$file" == "${BASH_SOURCE[0]}" ]]; then
		source "$file"
	fi
done

# Ensure this script is not run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	echo "This is a collection of helpers and cannot be run directly - source it instead" >&2
	exit 1
fi
