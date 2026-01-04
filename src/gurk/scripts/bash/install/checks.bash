check_install_vscode() {
	: '
	Check if Visual Studio Code is installed.

	Args:
	  None
	Outputs:
	  Path to the VSCode executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local vscode_path=$(command -v code)
	if [ -n "$vscode_path" ]; then
		echo "$vscode_path"
		return 0
	else
		return 1
	fi
}

check_install_conda() {
	: '
	Check if Conda (Miniconda/Anaconda) is installed.

	Args:
	  None
	Outputs:
	  Path to the Conda executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local conda_path=$(bash -ic 'echo $CONDA_EXE')
	if [ -n "$conda_path" ]; then
		echo "$conda_path"
		return 0
	else
		return 1
	fi
}

check_install_mamba() {
	: '
	Check if Mamba (Micromamba/Mamba) is installed.

	Args:
	  None
	Outputs:
	  Path to the Mamba executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local mamba_path=$(bash -ic 'echo $MAMBA_EXE')
	if [ -n "$mamba_path" ]; then
		echo "$mamba_path"
		return 0
	else
		return 1
	fi
}

# TODO: Seems to fail?
check_install_fzf() {
	: '
	Check if fzf is installed.

	Args:
	  None
	Outputs:
	  Path to the fzf executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local fzf_path=$(bash -ic 'command -v fzf || true')
	if [ -n "$fzf_path" ]; then
		echo "$fzf_path"
		return 0
	else
		return 1
	fi
}

check_install_loki_shell() {
	: '
	Check if Loki Shell Docker container is running.

	Args:
	  None
	Outputs:
	  Docker container info if running.
	Returns:
	  0 if running, 1 otherwise
	'
	local loki_container=$(docker ps -a | grep loki)
	if [ -n "$loki_container" ]; then
		echo "$loki_container"
		return 0
	else
		return 1
	fi
}

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

# TODO: Test if this works without reboot (thanks to modprobe)
check_install_nvidia_driver() {
	: '
	Check if NVIDIA driver is installed.

	Args:
	  None
	Outputs:
	  Path to the nvidia-smi executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	# TODO: bash -ic necessary?
	local nvidia_smi_path=$(bash -ic 'sudo modprobe nvidia && command -v nvidia-smi || true')
	if [ -n "$nvidia_smi_path" ]; then
		echo "$nvidia_smi_path"
		return 0
	else
		return 1
	fi
}

check_install_cuda() {
	: '
	Check if CUDA toolkit is installed.

	Args:
	  None
	Outputs:
	  Path to the nvcc executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	# TODO: bash -ic necessary?
	local nvcc_path=$(bash -ic 'command -v nvcc || true')
	if [ -n "$nvcc_path" ]; then
		echo "$nvcc_path"
		return 0
	else
		return 1
	fi
}

check_install_ros() {
	: '
	Check if ROS (ROS1 or ROS2) is installed.

	Args:
	  None
	Outputs:
	  Path to the roscore or ros2 executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local setup_script=""
	if [[ -d "/opt/ros/" ]]; then
		setup_script=$(sudo find /opt/ros/ -name "setup.bash" | head -n1)
	fi
	if [[ -f "$setup_script" ]]; then
		ros_path=$(source "$setup_script" && command -v roscore || command -v ros2)
		if [ -n "$ros_path" ]; then
			echo "$ros_path"
			return 0
		else
			return 1
		fi
	else
		return 1
	fi
}

# TODO (test install without starting window etc. - maybe import isaacsim as a module?)
check_install_isaacsim() {
	: '
	Check if NVIDIA Isaac Sim is installed.

	Args:
	  None
	Outputs:
	  Path to the Isaac Sim installation if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local isaacsim_path=$(bash -ic 'echo ${ISAACSIM_PATH}')
	local isaacsim_python_exe=$(bash -ic 'echo ${ISAACSIM_PYTHON_EXE}')
	if [ -d "$isaacsim_path" ] && [ -f "$isaacsim_python_exe" ]; then
		echo "$isaacsim_path"
		return 0
	else
		return 1
	fi
	# ${ISAACSIM_PYTHON_EXE} -c "print('Isaac Sim configuration is now complete.')"
	# ${ISAACSIM_PYTHON_EXE} ${ISAACSIM_PATH}/standalone_examples/api/isaacsim.core.api/add_cubes.py
}

# TODO: (test install without starting window etc.)
# TODO: Maybe return path to env (given by conda cmd) or somehow path to installation directory?
check_install_isaaclab() {
	: '
	Check if NVIDIA Isaac Lab is installed.

	Args:
	  None
	Outputs:
	  None
	Returns:
	  0 if installed (with conda), 1 otherwise
	'
	if bash -ic "conda env list" | grep isaaclab; then
		return 0
	else
		return 1
	fi
}

check_gcc_version() {
	: '
	Check if the default GCC version is compatible with the kernel compiler version.

	Args:
	  None
	Outputs:
	  Compatibility message.
	Returns:
	  0 if compatible, 1 otherwise
	'
	# Get kernel compiler version
	local kernel_cc=$(grep "CONFIG_CC_VERSION_TEXT" /boot/config-$(uname -r) | cut -d'"' -f2)
	local kernel_major=$(echo "$kernel_cc" | grep -oP '\bgcc-\K[0-9]+')
	if [[ -z "$kernel_cc" || -z "$kernel_major" ]]; then
		echo "Cannot determine kernel compiler version - Aborting"
		return 1
	fi

	# Get default GCC version
	local gcc_ver=$(gcc -dumpversion 2>/dev/null)
	local gcc_major=$(echo "$gcc_ver" | cut -d. -f1)
	if [[ -z "$gcc_ver" || -z "$gcc_major" ]]; then
		echo "Cannot determine GCC version - Aborting"
		return 1
	fi

	# Compare
	if [ "$kernel_major" -eq "$gcc_major" ]; then
		echo "Kernel and default GCC major versions match and are thus likely compatible"
		return 0
	elif [ "$gcc_major" -gt "$kernel_major" ]; then
		echo "Default GCC ($gcc_major) is newer than kernel GCC ($kernel_major), and thus may be incompatible - Aborting"
		return 1
	else
		echo "Default GCC ($gcc_major) is older than kernel GCC ($kernel_major), and is thus likely incompatible - Aborting"
		return 1
	fi
}
