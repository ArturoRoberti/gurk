source "$(dirname "${BASH_SOURCE[0]}")/checks.bash"

install_conda() {
	: "
	Install Conda (Miniconda/Anaconda)

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

	# Check if Conda is already installed
	# TODO: Maybe allow switching between miniconda/anaconda;
	# 		i.e. specify which one to check as well
	if check_install_conda && [[ "$FORCE" == false ]]; then
		log_step "Conda is already installed - Exiting"
		return 0
	fi

	# (STEP) Installing Requirement(s)
	apt_install wget

	# Get OS type/name
	local os_type="${SYSTEM_INFO[type]}"
	case "$os_type" in
		linux)
			os_name="Linux"
			;;
		darwin)
			os_name="MacOSX"
			;;
		windows)
			os_name="Windows"
			;;
		*)
			log_step "Unsupported OS type: ${SYSTEM_INFO[type]}" true
			return 1
			;;
	esac

	# Download latest Conda installation script
	local conda_script_url=""
	local conda_install_name=""
	local base_url="https://repo.anaconda.com"
	if [[ $CONDA_CONDA_DISTRIBUTION == "miniconda" ]]; then
		conda_script_url="${base_url}/miniconda/Miniconda3-latest-${os_name}-${SYSTEM_INFO[kernel]}.sh"
		conda_install_name=".miniconda"
	elif [[ $CONDA_CONDA_DISTRIBUTION == "anaconda" ]]; then
		local latest=$(curl -s ${base_url}/archive/ |
			grep -Eo "Anaconda3-[0-9]+\.[0-9]+(-[0-9]+)?-${os_name}-${SYSTEM_INFO[kernel]}\.sh" |
			sort -V |
			tail -n1)
		conda_script_url="${base_url}/archive/$latest"
		conda_install_name=".anaconda"
	else
		log_step "Unsupported conda distribution: ${CONDA_CONDA_DISTRIBUTION}" true
		return 1
	fi

	# (STEP) Downloading conda installation script
	local conda_script=$(mktemp --suffix=".sh")
	local conda_install_path="$HOME/${conda_install_name}"
	wget $conda_script_url -O $conda_script

	# (STEP) Installing Conda
	bash $conda_script -b -p $conda_install_path
	rm $conda_script

	# (STEP) Setting up Conda
	$conda_install_path/bin/conda init
	bash -ic 'conda config --set auto_activate false'

	# (STEP) Accepting ToS
	local accept_tos_cmd="conda tos accept --override-channels --channel"
	bash -ic "$accept_tos_cmd https://repo.anaconda.com/pkgs/main"
	bash -ic "$accept_tos_cmd https://repo.anaconda.com/pkgs/r"

	# Verify installation
	check_install_conda
}

# NOTE: To uninstall run "micromamba shell deinit" and then remove "~/.micromamba" and "~/.local/bin/micromamba" folders
_install_micromamba() {
	: "
	Install Micromamba

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Check if micromamba is already installed
	if check_install_mamba && [[ "$FORCE" == false ]]; then
		log_step "Micromamba is already installed - Exiting"
		return 0
	fi

	# Install requirements
	log_step "Installing Requirement(s)"
	apt_install curl

	# Install Micromamba
	log_step "Installing Micromamba"
	curl -L https://micro.mamba.pm/install.sh | PREFIX_LOCATION="$HOME/.micromamba" "${SHELL}"

	# Verify installation
	check_install_mamba
}

# NOTE: To uninstall run "mamba shell deinit" and then "conda remove -y mamba"
_install_mamba() {
	: "
	Install Mamba

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Check if mamba is already installed
	if check_install_mamba && [[ "$FORCE" == false ]]; then
		log_step "Mamba is already installed - Exiting"
		return 0
	fi

	# Check if conda is installed
	if ! check_install_conda; then
		log_step "Conda is not installed (Task-Dependency) - Exiting" true
		return 1
	fi

	# Install Mamba via Conda
	log_step "Installing Mamba"
	bash -ic 'conda install -y -c conda-forge mamba'
	bash -ic 'mamba shell init'

	# Verify installation
	check_install_mamba
}

install_mamba() {
	: "
	Install (Micro)Mamba - Micromamba prioritized over Mamba (if both specified)

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# TODO: ToS acceptance for mamba required?

	# Parse task args
	parse_task_args "$@"

	# TODO: Maybe allow switching between micromamba/mamba;
	# 		i.e. specify which one to check as well

	# (STEP) Installing (Micro)Mamba
	if [[ $CONDA_MAMBA_DISTRIBUTION == "micromamba" ]]; then
		_install_micromamba "$@"
	elif [[ $CONDA_MAMBA_DISTRIBUTION == "mamba" ]]; then
		_install_mamba "$@"
	else
		log_step "Unsupported mamba distribution: ${CONDA_MAMBA_DISTRIBUTION}" true
		return 1
	fi
}
