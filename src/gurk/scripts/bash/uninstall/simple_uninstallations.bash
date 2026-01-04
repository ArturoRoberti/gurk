uninstall_fzf() {
	: '
	Uninstall fzf

	Args:
	  None
	Outputs:
	  Log messages indicating the current progress and uninstallation outputs
	Returns:
	  0 if successful (or already uninstalled), 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Test if fzf is installed
	if ! check_install_fzf && [[ "$FORCE" == false ]]; then
		log_step "fzf is not installed - Exiting"
		return 0
	fi

	{
		~/.fzf/uninstall
		rm -rf ~/.fzf
	} || true

	# Verify installation
	if check_install_fzf; then
		log_step "fzf uninstallation failed" true
		return 1
	fi
}

uninstall_loki_shell() {
	: '
	Uninstall loki-shell

	Args:
	  None
	Outputs:
	  Log messages indicating the current progress and uninstallation outputs
	Returns:
	  0 if successful (or already uninstalled), 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Test if loki-shell is installed
	if ! check_install_loki_shell && [[ "$FORCE" == false ]]; then
		log_step "loki-shell is not installed - Exiting"
		return 0
	fi

	{
		docker rm -f loki-shell
		rm -rf ~/.loki-shell
		sed -i "/#* BEGIN LOKI-SHELL #*/,/#* END LOKI-SHELL #*/d" "${HOME}/.bashrc"
	} || true

	# Verify installation
	if check_install_loki_shell; then
		log_step "loki-shell uninstallation failed" true
		return 1
	fi
}
