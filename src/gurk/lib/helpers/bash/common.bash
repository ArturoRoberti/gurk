getent_passwd() {
	: "
    Retrieve specific fields from the system's user database for a given user.

    Args:
    - User (str|int): Username or user ID
    - Field (str):    One of username, uid, gid, gecos, home, shell
    Outputs:
      The requested field value
    Returns:
    - 0 if successful
    - 1 if user not found
    - 3 if unknown field
    "
	local user="$1"
	local field="$2"

	local -A idx=(
		[username]=0
		[uid]=2
		[gid]=3
		[gecos]=4
		[home]=5
		[shell]=6
	)

	[[ -v idx[$field] ]] || {
		echo "Error: unknown field '$field'" >&2
		return 3
	}

	local entry
	entry=$(getent passwd "$user") || {
		echo "Error: user '$user' not found" >&2
		return 1
	}

	IFS=':' read -ra parts <<<"$entry"
	printf '%s\n' "${parts[${idx[$field]}]}"
}
