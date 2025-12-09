check_configure_bashrc() {
  : '
    Check if the ~/.bashrc has been configured with the custom lines.
    '
  if marker_in_file "$HOME/.bashrc" "BASHRC CONFIGURATION"; then
    log_step "~/.bashrc is already configured"
    return 0
  else
    log_step "~/.bashrc is not configured"
    return 1
  fi
}
