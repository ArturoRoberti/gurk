configure_bashrc() {
	: '
	Add custom lines to ~/.bashrc.

	Args:
	  - Configuration Args
	Outputs:
	  Log messages indicating the current progress
	Returns:
	  0 if configured, 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Check if config file is provided
	if [ -z "$CONFIG_FILE" ]; then
		log_step "Skipping configuration of the ~/.bashrc, as no task config file is provided" true
		return 0
	fi

	# Append custom bashrc lines to ~/.bashrc
	local check_existing=true
	if [[ "$FORCE" == true ]]; then
		check_existing=false
	fi
	write_marked "$CONFIG_FILE" "$HOME/.bashrc" "$check_existing"

	# Verify configuration
	check_configure_bashrc
}
