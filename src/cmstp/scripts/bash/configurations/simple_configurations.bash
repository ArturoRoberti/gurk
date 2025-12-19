#!/usr/bin/env bash

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
  # Check if already configured
  if check_configure_bashrc && [[ "$FORCE" == false ]]; then
    log_step "~/.bashrc is already configured - Exiting"
    return 0
  fi
  # TODO?: Remove marker in case of "--force" option

  # Parse config args
  get_config_args "$@"
  if [ -z "$CONFIG_FILE" ]; then
    log_step "Skipping configuration of the ~/.bashrc, as no task config file is provided" true
    return 0
  fi

  # Append custom bashrc lines to ~/.bashrc
  log_to_file "$CONFIG_FILE" "$HOME/.bashrc" "BASHRC CONFIGURATION"

  # Verify configuration
  check_configure_bashrc
}
