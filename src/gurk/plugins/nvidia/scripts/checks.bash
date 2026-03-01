check_install_nvidia_driver() {
	: "
	Check if NVIDIA driver is installed.

	Args:
	  None
	Outputs:
	  Path to the nvidia-smi executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	# Ensure kernel module is loaded
	sudo modprobe nvidia

	# Actual check
	local nvidia_smi_path=$(command -v nvidia-smi)
	if [ -n "$nvidia_smi_path" ]; then
		echo "$nvidia_smi_path"
		return 0
	else
		return 1
	fi
}

check_install_cuda() {
	: "
	Check if CUDA toolkit is installed.

	Args:
	  None
	Outputs:
	  Path to the nvcc executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local nvcc_path=$(command -v nvcc)
	if [ -n "$nvcc_path" ]; then
		echo "$nvcc_path"
		return 0
	else
		return 1
	fi
}

# TODO (test install without starting window etc. - maybe import isaacsim as a module?)
check_install_isaacsim() {
	: "
	Check if NVIDIA Isaac Sim is installed.

	Args:
	  None
	Outputs:
	  Path to the Isaac Sim installation if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
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
	: "
	Check if NVIDIA Isaac Lab is installed.

	Args:
	  None
	Outputs:
	  None
	Returns:
	  0 if installed (with conda), 1 otherwise
	"
	if bash -ic "conda env list" | grep isaaclab; then
		return 0
	else
		return 1
	fi
}

check_gcc_version() {
	: "
	Check if the default GCC version is compatible with the kernel compiler version.

	Args:
	  None
	Outputs:
	  Compatibility message.
	Returns:
	  0 if compatible, 1 otherwise
	"
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
