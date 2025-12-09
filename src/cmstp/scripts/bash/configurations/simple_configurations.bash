#!/usr/bin/env bash

configure_bashrc() {
  : '
    Add custom lines to the basrc.
    '
  # Check if already configured
  if check_configure_bashrc; then
    log_step "~/.bashrc is already configured - Exiting"
    return 0
  fi
  # TODO?: Remove marker in case of "--force" option

  # Parse config args
  get_config_args "$@"
  if [ -z "$CONFIG_FILE" ]; then
    log_step "Skipping configuration of the ~/.bashrc, as no task config file is provided" false
    return 0
  fi

  # Append custom bashrc lines to ~/.bashrc
  log_to_file "$CONFIG_FILE" "$HOME/.bashrc" "BASHRC CONFIGURATION"

  # Verify configuration
  check_configure_bashrc
}
