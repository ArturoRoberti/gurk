source "$(dirname "${BASH_SOURCE[0]}")/checks.bash"

install_vscode() {
	: '
	Install VSCode from source

	Args:
	  - Configuration Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Check if VSCode is already installed
	if check_install_vscode && [[ "$FORCE" == false ]]; then
		log_step "VSCode is already installed - Exiting"
		return 0
	fi

	# (STEP) Installing Requirement(s)
	apt_install software-properties-common apt-transport-https wget

	# (STEP) Adding VSCode APT Repository
	wget -qO- https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/microsoft.gpg >/dev/null
	sudo add-apt-repository -y "deb [arch=${SYSTEM_INFO[arch]}] https://packages.microsoft.com/repos/code stable main"
	sudo apt-get update

	# TODO: Fix issues with "classic APT format (.list)" vs. newer “deb822 format (.sources)" (found on fresh ubuntu24)
	#       "Old" file is cat "/etc/apt/sources.list.d/archive_uri-https_packages_microsoft_com_repos_code-noble.list"
	#       "New" file is cat "/etc/apt/sources.list.d/vscode.sources"

	# (STEP) Installing VSCode
	apt_install code

	# Verify installation
	check_install_vscode
}
