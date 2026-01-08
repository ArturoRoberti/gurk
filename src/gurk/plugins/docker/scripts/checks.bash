check_install_docker() {
	: '
	Check if Docker is installed.

	Args:
	  None
	Outputs:
	  Path to the Docker executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local docker_path=$(command -v docker)
	if [ -n "$docker_path" ]; then
		echo "$docker_path"
	else
		return 1
	fi
}

check_install_container_toolkit() {
	: '
	Check if NVIDIA Container Toolkit is installed.

	Args:
	  None
	Outputs:
	  Path to the nvidia-ctk executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local nvidia_ctk_path=$(command -v nvidia-ctk)
	if [ -n "$nvidia_ctk_path" ]; then
		echo "$nvidia_ctk_path"
		return 0
	else
		return 1
	fi
}
