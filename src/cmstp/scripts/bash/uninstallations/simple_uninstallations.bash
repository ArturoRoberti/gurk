uninstall_fzf() {
  : '
    Uninstall fzf
    '
  # Test if fzf is installed
  if ! check_install_fzf; then
    log_step "fzf is not installed - Exiting"
    return 0
  fi

  ~/.fzf/uninstall
  rm -rf ~/.fzf

  # Verify installation
  if check_install_fzf; then
    log_step "fzf uninstallation failed"
    return 1
  fi
}

uninstall_loki_shell() {
  : '
    Uninstall loki-shell
    '
  # Test if loki-shell is installed
  if ! check_install_loki_shell; then
    log_step "loki-shell is not installed - Exiting"
    return 0
  fi

  docker rm -f loki-shell
  sudo rm -rf ~/.loki-shell
  sed -i "/#* BEGIN LOKI-SHELL #*/,/#* END LOKI-SHELL #*/d" "${HOME}/.bashrc"

  # Verify installation
  if check_install_loki_shell; then
    log_step "loki-shell uninstallation failed"
    return 1
  fi
}
