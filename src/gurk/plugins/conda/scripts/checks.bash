check_install_conda() {
	: "
	Check if Conda (Miniconda/Anaconda) is installed.

	Args:
	  None
	Outputs:
	  Path to the Conda executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local conda_path=$(bash -ic 'echo $CONDA_EXE')
	if [ -n "$conda_path" ]; then
		echo "$conda_path"
		return 0
	else
		return 1
	fi
}

check_install_mamba() {
	: "
	Check if Mamba (Micromamba/Mamba) is installed.

	Args:
	  None
	Outputs:
	  Path to the Mamba executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local mamba_path=$(bash -ic 'echo $MAMBA_EXE')
	if [ -n "$mamba_path" ]; then
		echo "$mamba_path"
		return 0
	else
		return 1
	fi
}
