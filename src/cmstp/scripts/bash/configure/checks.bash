check_configure_bashrc() {
	: '
	Check if the ~/.bashrc has been configured with the custom lines.

	Args:
	  None
	Outputs:
	  Log messages indicating the current progress
	Returns:
	  0 if configured, 1 otherwise
	'
	if markers_exist "$HOME/.bashrc"; then
		log_step "~/.bashrc is already configured"
		return 0
	else
		log_step "~/.bashrc is not configured"
		return 1
	fi
}
