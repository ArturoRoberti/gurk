check_install_fzf() {
	: "
	Check if fzf is installed.

	Args:
	  None
	Outputs:
	  Path to the fzf executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local fzf_path=$(bash -ic 'command -v fzf || true')
	if [ -n "$fzf_path" ]; then
		echo "$fzf_path"
		return 0
	else
		return 1
	fi
}

check_install_loki_shell() {
	: "
	Check if Loki Shell Docker container is running.

	Args:
	  None
	Outputs:
	  Docker container info if running.
	Returns:
	  0 if running, 1 otherwise
	"
	local loki_container=$(docker ps -a | grep loki)
	if [ -n "$loki_container" ]; then
		echo "$loki_container"
		return 0
	else
		return 1
	fi
}
