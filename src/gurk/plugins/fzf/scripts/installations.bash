source "$(dirname "${BASH_SOURCE[0]}")/checks.bash"

install_fzf() {
	: "
	Install fzf (fuzzy finder)

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

	# Test if fzf is already installed
	if check_install_fzf && [[ "$FORCE" == false ]]; then
		log_step "fzf is already installed - Exiting"
		return 0
	fi

	# (STEP) Installing Requirement(s)
	apt_install git

	# (STEP) Installing fzf
	git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
	~/.fzf/install --all

	# Verify installation
	check_install_fzf
}

install_loki_shell() {
	: "
	Install loki-shell (fzf support over docker containers)

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

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
