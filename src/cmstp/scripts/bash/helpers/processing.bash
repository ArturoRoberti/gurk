#################################################################################################################
################################################ File Processing ################################################
#################################################################################################################

# JSON
_json_lines() {
	# Internal helper to read simple JSON(C) files (just key-value pairs) entry by entry
	local file=$1
	sed 's://.*$::; s:#.*$::' "$file" |
		jq -c 'to_entries[]'
}
_json_read() {
	# Internal helper to read simple JSON(C) files (just key-value pairs) entry by entry
	local line
	if IFS= read -r line; then
		key=$(jq -r '.key' <<<"$line")
		if jq -e '.value | arrays' >/dev/null <<<"$line"; then
			# Populate Bash array
			mapfile -t value < <(jq -r '.value[]' <<<"$line")
		else
			# Scalar
			value=$(jq -r '.value' <<<"$line")
		fi
		return 0
	else
		return 1
	fi
}

# TXT
_txt_lines() {
	# Internal helper to read TXT files line by line
	local file=$1
	while IFS= read -r line || [[ -n $line ]]; do
		# Trim + remove comments
		line="${line%%#*}"
		line="${line#"${line%%[![:space:]]*}"}"
		line="${line%"${line##*[![:space:]]}"}"
		[[ -z $line ]] && continue
		echo "$line"
	done <"$file"
}
_txt_read() {
	# Internal helper to read TXT files line by line
	if IFS= read -r line; then
		return 0
	else
		return 1
	fi
}

# Get file extension
get_file_extension() {
	: '
	Get the file extension from a filename.

	Args:
	  - file:   Path to the file.
	Outputs:
	  File extension (lowercase)
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local file=$1
	local ext="${file##*.}"
	echo "${ext,,}"
}

# Interfaces
_lines() {
	: '
	Read lines/elements from a file based on its extension (together with '_read' function).

	Usage:
	```bash
	while _read "$file"; do
	  # Use $line (TXT file), or $key and $value (JSON(C) file)
	done < <(_lines "$file")
	```

	Args:
	  - file:   Path to the file.
	Outputs:
	  Lines/elements from the file.
	Returns:
	  0 if successful, 1 otherwise (incl. unsupported extension)
	'
	local file=$1
	local ext=$(get_file_extension "$file")

	case "$ext" in
		json | jsonc) _json_lines "$file" ;;
		txt) _txt_lines "$file" ;;
		*)
			echo "Unsupported file extension: $ext" >&2
			return 1
			;;
	esac
}
_read() {
	: '
	Read lines/elements from a file based on its extension (together with '_read' function).

	Usage:
	```bash
	while _read "$file"; do
	  # Use $line (TXT file), or $key and $value (JSON(C) file)
	done < <(_lines "$file")
	```

	Args:
	  - file:   Path to the file.
	Outputs:
	  Lines/elements from the file.
	Returns:
	  0 if successful, 1 otherwise (incl. unsupported extension)
	'
	local file=$1
	local ext=$(get_file_extension "$file")
	case "$ext" in
		json | jsonc) _json_read ;;
		txt) _txt_read ;;
		*)
			return 1
			;;
	esac
}

#################################################################################################################
##################################################### Other #####################################################
#################################################################################################################

remove_dots() {
	: '
	Remove all dots from a string.

	Args:
	  - input:   Input string.
	Outputs:
	  String without dots.
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local input="$1"
	echo "${input//./}"
}

_contains() {
	: '
	Check if an array (indexed or associative) or scalar contains any of the specified values/keys (match case).

	Usage:
	```bash
	if _contains arr_name str1 str2 ...; then
	  # Found
	else
	  # Not found
	fi
	```

	Args:
	  - arr_name:   Name of the array (indexed or associative) or scalar variable.
	  - ...:        Values/keys to search for.
	Outputs:
	  None
	Returns:
	  0 if any key found, 1 otherwise
	'
	local arr_name=$1
	local -n arr=$arr_name # nameref to array

	# Detect array type: "indexed" or "associative"
	local type=$(declare -p "$arr_name" 2>/dev/null)

	shift # Shift to get the needles
	if [[ $type =~ "declare -A" ]]; then
		# Associative array: check KEYS
		for needle in "$@"; do
			if [[ -v arr["$needle"] ]]; then
				return 0
			fi
		done
	else
		# Indexed array (or other scalar type): check VALUES
		for needle in "$@"; do
			for element in "${arr[@]}"; do
				if [[ $element == "$needle" ]]; then
					return 0
				fi
			done
		done
	fi

	return 1
}

_wait_dpkg() {
	: '
	Install packages with dpkg lock waiting to avoid conflicts.

	Args:
	  - ...:   Command and arguments to run with dpkg lock.
	Outputs:
	  None
	Returns:
	  0 (unless an unexpected error occurs)
	'
	sudo flock /var/lib/dpkg/lock-frontend "$@"
}

dpkg_install() {
	: '
	Install debian packages safely

	Args:
	  - packages:   Debian package files to install.
	Outputs:
	  None
	Returns:
	  0 (unless an unexpected error occurs)
	'
	_wait_dpkg sudo dpkg -i "$@"
}

apt_install() {
	: '
	Install apt packages safely

	Args:
	  - packages:   APT packages to install.
	Outputs:
	  None
	Returns:
	  0 (unless an unexpected error occurs)
	'
	_wait_dpkg sudo apt-get install -y "$@"
}

revert_sudo_permissions() {
	: '
	Revert ownership and permissions of folders/files created with sudo to the original user.

	Args:
	  - target:   Path to the target file or directory.
	Outputs:
	  None
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local target="$1"

	# Change ownership
	sudo chown -R "$SUDO_USER:$SUDO_USER" "$target"

	# Directories: 775
	sudo find "$target" -type d -exec chmod 775 {} +

	# Files: 664
	sudo find "$target" -type f -exec chmod 664 {} +
}
