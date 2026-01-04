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
	apt_install code # TODO: Hangs (probably due to interactive window - maybe set (generally, not just here the interactiveness env variable?))

	# Verify installation
	check_install_vscode
}

install_fzf() {
	: '
	Install fzf (fuzzy finder)

	Args:
	  None
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Test if fzf is already installed
	if check_install_fzf && [[ "$FORCE" == false ]]; then
		log_step "fzf is already installed - Exiting"
		return 0
	fi

	# (STEP) Installing Requirement(s)
	apt_install git

	# (STEP) Installing fzf
	# TODO: Still seems to fail, although it works
	git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
	~/.fzf/install --all

	# Verify installation
	check_install_fzf
}

install_loki_shell() {
	: '
	Install loki-shell (fzf support over docker containers)

	Args:
	  None
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Test if loki-shell is already installed
	if check_install_loki_shell && [[ "$FORCE" == false ]]; then
		log_step "loki-shell is already installed - Exiting"
		return 0
	elif ! check_install_docker; then
		log_step "Docker must be installed before installing loki-shell" true
		return 1
	fi

	# (STEP) Installing Requirement(s)
	apt_install git

	# (STEP) Installing loki-shell (with docker)
	git clone --depth 1 https://github.com/slim-bean/loki-shell.git ~/.loki-shell
	printf "y\ny\n\n" | ~/.loki-shell/install

	# Verify installation
	check_install_loki_shell
}
