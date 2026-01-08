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
	: '
	Check if CUDA toolkit is installed.

	Args:
	  None
	Outputs:
	  Path to the nvcc executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
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
