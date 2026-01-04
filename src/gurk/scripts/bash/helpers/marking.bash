_gurk_marker() {
	: '
	Generate a GURK marker string.

	Args:
	  - type:   "START" or "END"
	Outputs:
	  None
	Returns:
	  Marker string
	'
	local type="$1"
	if [[ "$type" == "START" ]]; then
		local n_hashes=20
	elif [[ "$type" == "END" ]]; then
		local n_hashes=21
	else
		log_step "(_gurk_marker) Invalid marker type '$type'" true
		return 1
	fi

	local hashes=$(printf '#%.0s' $(seq 1 $n_hashes))
	echo -e "${hashes} GURK ${type} ${hashes}"
}

_marker_exists() {
	: '
	Check if a marker exists in a file.

	Args:
	  - file:     Path to the file.
	  - marker:   Marker string to search for
	Outputs:
	  Number of occurrences of the marker
	Returns:
	  0 if exactly one marker is found, 1 otherwise
	'
	local file="$1"
	local marker="$2"
	if [ ! -f "$file" ]; then
		return 1
	fi

	local marker_count=$(grep -cE "$marker" "$file")
	echo "$marker_count"

	[ "$marker_count" -eq 1 ]
}

markers_exist() {
	: '
	Check if both start and end markers exist in a file.

	Args:
	  - file:           Path to the file.
	  - start_marker:   Start marker string (default: GURK start marker)
	  - end_marker:     End marker string (default: GURK end marker)
	Outputs:
	  None
	Returns:
	  0 if both markers are found exactly once, 1 otherwise
	'
	local file="$1"
	local start_marker="${2:-$(_gurk_marker 'START')}"
	local end_marker="${3:-$(_gurk_marker 'END')}"

	(_marker_exists "$file" "$start_marker" && _marker_exists "$file" "$end_marker") >/dev/null
}

_insert_around_marker() {
	: '
	Write a message around a specific marker in a file.

	Args:
	  - message:   Message string to write.
	  - file:      Path to the file.
	  - marker:    Marker string to search for.
	  - position:  "before" or "after"
	Outputs:
	  None
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local message="$1"
	local file="$2"
	local marker="$3"
	local position="$4"
	if [ ! -f "$file" ]; then
		log_step "(write_after) File not found: $file" true
		return 1
	fi

	local message_escaped=$(printf '%s' "$message" | sed 's/\\/\\\\/g')
	awk -v msg="$message_escaped" -v marker="$marker" -v pos="$position" '
		$0 ~ marker && pos=="before" {
		print msg
		print ""
		}
		{ print }
		$0 ~ marker && pos=="after" { print msg }
	' "$file" >"$file.tmp" && mv "$file.tmp" "$file"
}

_insert_missing_markers() {
	: '
	Ensure that both start and end markers exist in a file.

	Args:
	  - file:           Path to the file.
	  - start_marker:   Start marker string (default: GURK start marker)
	  - end_marker:     End marker string (default: GURK end marker)
	Outputs:
	  None
	Returns:
	  1 if an incompatible marker state is found, 0 otherwise
	'
	local file="$1"
	if [ ! -f "$file" ]; then
		log_step "(_insert_missing_markers) File not found: $file" true
		return 1
	fi
	local start_marker="${2:-$(_gurk_marker 'START')}"
	local end_marker="${3:-$(_gurk_marker 'END')}"

	# Check existing markers
	local n_start_markers=$(_marker_exists "$file" "$start_marker")
	local n_end_markers=$(_marker_exists "$file" "$end_marker")
	if [[ $n_start_markers -eq 0 && $n_end_markers -eq 0 ]]; then
		# Add both markers if none exist
		{
			echo -e "\n$start_marker"
			echo -e "\n$end_marker"
		} >>"$file"
	elif [[ $n_start_markers -eq 1 && $n_end_markers -eq 0 ]]; then
		# Add end marker if only start marker exists
		_insert_around_marker "$end_marker" "$file" "$start_marker" "after"
	elif [[ $n_start_markers -eq 0 && $n_end_markers -eq 1 ]]; then
		# Add start marker if only end marker exists
		_insert_around_marker "$start_marker" "$file" "$end_marker" "before"
	elif [[ $n_start_markers -eq 1 && $n_end_markers -eq 1 ]]; then
		# Markers already found - do nothing
		:
	else
		# Unsure/incompatible marker state
		return 1
	fi
}

write_marked() {
	: '
	Log a message or file content to a file, wrapped with GURK start and end markers.

	Args:
	  - message:          Message string or filepath to log from.
	  - file:             Path to the destination file.
	  - check_existing:   Whether or not to check for existing message to avoid duplication (default: false).
	Outputs:
	  None
	Returns:
	  0, unless the file does not exist or has incompatible marker state
	'
	local message="$1"
	local file="$2"
	if [ ! -f "$file" ]; then
		log_step "(write_marked) File not found: $file" true
		return 1
	fi
	local check_existing="${3:-false}"

	# Prepare content to insert
	local content
	if [ -f "$message" ]; then
		content=$(cat "$message")
	else
		content="$message"
		# Check for existing content
		if [ "$check_existing" = true ] && grep -Fq "$content" "$file"; then
			log_step "(write_marked) '$content' already exists in $file - Skipping"
			return 0
		fi
	fi

	# Get markers
	local start_marker="$(_gurk_marker 'START')"
	local end_marker="$(_gurk_marker 'END')"

	# Check existing markers
	if ! _insert_missing_markers "$file"; then
		log_step "(write_marked) Skipping, as file '$file' has incompatible marker state" true
		return 1
	fi

	# Insert content
	_insert_around_marker "$content" "$file" "$end_marker" "before"
}

remove_markers() {
	: '
	Remove all sections wrapped by the GURK markers from a file.

	Args:
	  - file:               Path to the file.
	  - remove_inbetween:   Whether or not to remove content between markers (default: true)
	  - start_marker:       Start marker string (default: GURK start marker)
	  - end_marker:         End marker string (default: GURK end marker)
	Outputs:
	  None
	Returns:
	  0, unless the file does not exist or has incompatible marker state
	'
	local file="$1"
	if [ ! -f "$file" ]; then
		return 1
	fi
	local remove_inbetween="${2:-true}"
	local start_marker="${3:-$(_gurk_marker 'START')}"
	local end_marker="${4:-$(_gurk_marker 'END')}"

	# Check existing markers
	if ! _insert_missing_markers "$file" "$start_marker" "$end_marker"; then
		log_step "(remove_markers) Skipping, as file '$file' has incompatible marker state" true
		return 1
	fi
	cat "$file"

	if [ "$remove_inbetween" = false ]; then
		# Remove only markers, keep in-between content
		sed -i "/$start_marker/d" "$file"
		sed -i "/$end_marker/d" "$file"
	else
		# Use sed to delete from start to end marker (inclusive)
		sed -i "/$start_marker/,/$end_marker/d" "$file"
	fi
}
