get_latest_isaacsim_version() {
  : '
    Function to get the latest Isaac Sim version from release notes
    '
  local URL="https://docs.isaacsim.omniverse.nvidia.com/latest/overview/release_notes.html"
  curl -s "$URL" |
    awk '/<section id="release-notes">/,/<\/section>/' |
    grep -m1 -Eo '<h2>[0-9]+\.[0-9]+\.[0-9]+' |
    sed -E 's/<h2>//'
}

# TODO: Test (looks good, at least for newest version)
install_isaacsim() {
  : '
    Function to install Isaac Sim (only officially supported versions)
    '
  # Parse config args
  get_config_args "$@"

  # Check if IsaacSim is already installed
  if check_install_isaacsim; then
    log_step "IsaacSim is already installed - Exiting"
    return 0
  fi

  # Check OS type
  if [[ "${SYSTEM_INFO[type]}" != "linux" && "${SYSTEM_INFO[type]}" != "windows" ]]; then
    error_msg "Unsupported OS type for IsaacSim: ${SYSTEM_INFO[type]} (only linux/windows supported)"
    return 1
  fi

  # (STEP) Installing Requirement(s)
  apt_install wget unzip

  # (STEP) Determining requested IsaacSim version
  local isaacsim_version=""
  if _contains REMAINING_ARGS "latest"; then
    # (1st Priority) Use latest available version
    isaacsim_version=$(get_latest_isaacsim_version)
  else
    # (2nd Priority) Use specified version
    for version in "${REMAINING_ARGS[@]}"; do
      if [[ "$version" == 4.* || "$version" == 5.* ]]; then
        isaacsim_version="$version"
        break
      fi
    done
  fi
  if [ -z "$isaacsim_version" ]; then
    error_msg "No (valid) IsaacSim version specified (latest, 4.*, 5.*)"
    return 1
  fi

  # (STEP) Downloading IsaacSim version $isaacsim_version (this may take a while)...
  local download_url=""
  local base_download_url="https://download.isaacsim.omniverse.nvidia.com/isaac-sim-standalone"
  if [[ ${isaacsim_version} == 4.0.0 ]]; then
    download_url="${base_download_url}%404.0.0-rc.21%2B4.0.13872.3e3cb0c9.gl.${SYSTEM_INFO[type]}-${SYSTEM_INFO[kernel]}.release.zip"
  elif [[ ${isaacsim_version} == 4.1.0 ]]; then
    download_url="${base_download_url}%404.1.0-rc.7%2B4.1.14801.71533b68.gl.${SYSTEM_INFO[type]}-${SYSTEM_INFO[kernel]}.release.zip"
  elif [[ ${isaacsim_version} == 4.2.0 ]]; then
    download_url="${base_download_url}%404.2.0-rc.18%2Brelease.16044.3b2ed111.gl.${SYSTEM_INFO[type]}-${SYSTEM_INFO[kernel]}.release.zip"
  else
    download_url="${base_download_url}-${isaacsim_version}-${SYSTEM_INFO[type]}-${SYSTEM_INFO[kernel]}.zip"
  fi
  local download_path=$(mktemp --suffix=".zip")
  if ! wget "$download_url" -O "$download_path"; then
    error_msg "Failed to download IsaacSim version ${isaacsim_version} from ${download_url}"
    return 1
  fi

  # (STEP) Unzipping IsaacSim to $HOME/isaac/isaacsim
  local install_path="$HOME/isaac/isaacsim"
  mkdir -p "$install_path"
  if ! unzip "$download_path" -d "$install_path"; then
    error_msg "Failed to unzip IsaacSim version ${isaacsim_version} to ${install_path}"
    return 1
  fi
  revert_sudo_permissions "$install_path"

  # Add environment variables to bashrc - TODO: Use util for this
  local bashrc_path="${HOME}/.bashrc"
  {
    echo ""
    echo "# IsaacSim Environment Variables"
    echo "export ISAACSIM_PATH=\"${install_path}\""
    echo "export ISAACSIM_PYTHON_EXE=\"\${ISAACSIM_PATH}/python.sh\""
  } >>"$bashrc_path"

  # Verify installation
  check_install_isaacsim
}

get_latest_isaaclab_version() {
  : '
    Function to get the latest IsaacLab version from the version dropdown
    '
  local URL="https://isaac-sim.github.io/IsaacLab/main/index.html"
  curl -s "$URL" |
    grep -Eo '>[v]?[0-9]+\.[0-9]+\.[0-9]+<' |
    sed -E 's/[><]//g' |
    sort -V |
    tail -n1
}

# TODO: Test
install_isaaclab() {
  : '
    Function to install Isaac Lab (only officially supported versions)
    '
  # Parse config args
  get_config_args "$@"

  # Check if IsaacLab is already installed
  if check_install_isaaclab; then
    log_step "IsaacLab is already installed - Exiting"
    return 0
  elif ! check_install_isaacsim || ! check_install_conda; then
    error_msg "IsaacSim and Conda must be installed before installing IsaacLab"
    return 1
  fi
  local isaacsim_path=$(check_install_isaacsim)

  # (STEP) Installing Requirement(s)
  apt_install wget unzip
  apt_install cmake build-essential # required for isaaclab

  # (STEP) Determining requested IsaacLab version
  local isaaclab_version=""
  if _contains REMAINING_ARGS "recommended"; then
    # (1st Priority) Find best matching version for installed IsaacSim
    local isaacsim_version=$(head -n1 "${isaacsim_path}/VERSION" || true)
    if [[ -z "$isaacsim_version" ]]; then
      error_msg "Failed to determine installed IsaacSim version from ${isaacsim_path}/VERSION"
      return 1
    elif [[ "$isaacsim_version" != 4.* && "$isaacsim_version" != 5.* ]]; then
      error_msg "Unsupported IsaacSim version for IsaacLab: ${isaacsim_version} (only 4.*, 5.* supported)"
      return 1
    elif [[ "$isaacsim_version" == 4.0.0 || "$isaacsim_version" == 4.1.0 || "$isaacsim_version" == 4.2.0 ]]; then
      error_msg "IsaacSim versions older than 4.5.0 are not supported for the IsaacLab installation in this repo - please find and install a fitting IsaacLab version manually (see 'https://isaac-sim.github.io/IsaacLab' and use the toggle for older versions of IsaacLab)"
      return 1
    fi
    isaaclab_version=$(find_best_isaaclab "$isaacsim_version")
  else
    if _contains REMAINING_ARGS "latest"; then
      # (2nd Priority) Use latest available version
      isaaclab_version=$(get_latest_isaaclab_version)
    else
      # (Last Priority) Use specified version
      for version in "${REMAINING_ARGS[@]}"; do
        if [[ "$version" == v2.* ]]; then
          isaaclab_version="$version"
          break
        fi
      done
    fi
    # TODO: Test if the version works with installed isaacsim version
  fi
  if [ -z "$isaaclab_version" ]; then
    error_msg "No (valid) IsaacLab version found/specified (latest, v2.*)"
    return 1
  fi

  # (STEP) Downloading IsaacLab version $isaaclab_version (this may take a while)...
  local download_url="https://github.com/isaac-sim/IsaacLab/archive/refs/tags/${isaaclab_version}.zip"
  local download_path=$(mktemp --suffix=".zip")
  if ! wget "$download_url" -O "$download_path"; then
    error_msg "Failed to download IsaacLab version ${isaaclab_version} from ${download_url}"
    return 1
  fi

  # (STEP) Unzipping IsaacLab to $HOME/isaac/isaaclab
  local install_path="$HOME/isaac/isaaclab"
  local unzipped=$(mktemp -d)
  if ! unzip "$download_path" -d "$unzipped"; then
    error_msg "Failed to unzip IsaacLab version ${isaaclab_version} to ${install_path}"
    return 1
  fi
  mv "$unzipped"/* "$install_path"
  revert_sudo_permissions "$install_path"

  # Create symlink to isaacsim
  ln -s "${isaacsim_path}" "${install_path}/_isaac_sim"

  # (STEP) Creating conda environment
  bash -i ${install_path}/isaaclab.sh --conda

  # (STEP) Installing IsaacLab into conda environment
  bash -ic "conda run -n env_isaaclab ${install_path}/isaaclab.sh --install"

  # Verify installation
  check_install_isaaclab
}

find_best_isaaclab() {
  local isaacsim_version="$1"

  # Get IsaacLab version mappings
  local sim_version=$(echo "$isaacsim_version" | awk -F. '{print $1"."$2}')
  local readme=$(curl -s "https://raw.githubusercontent.com/isaac-sim/IsaacLab/main/README.md")
  local section=$(printf "%s" "$readme" | awk '
      /## Isaac Sim Version Dependency/ {flag=1; next}
      /^## / && flag {flag=0}
      flag
    ')
  local table=$(printf "%s" "$section" | grep '|' | sed 's/^[[:space:]]*//')
  local mappings=$(printf "%s" "$table" |
    tail -n +3 |
    awk -F '|' '{gsub(/`/, "", $2); gsub(/`/, "", $3); print $2 "|" $3}')

  # Get matching IsaacLab versions
  local matches=()
  while IFS='|' read -r lab_version sim_versions; do
    local normalized
    normalized=$(echo "$sim_versions" |
      sed -E 's/Isaac Sim//g; s/\// /g; s/[ ]+/ /g')

    for ver in $normalized; do
      if [ "$ver" = "$sim_version" ]; then
        matches+=("$lab_version")
      fi
    done
  done <<<"$mappings"

  # Return latest matching version
  if [ ${#matches[@]} -eq 0 ]; then
    echo "No compatible IsaacLab version found for IsaacSim $isaacsim_version"
    return 1
  fi
  # TODO: 'sed' inserted here bc of leading/trailing spaces in version strings and 'X' replacement:
  #       - See why there are spaces at all
  #       - Handle 'X' replacement better (e.g. see what exists, don't just replace with 0)
  printf "%s\n" "${matches[@]}" |
    sed 's/^[[:space:]]*//; s/[[:space:]]*$//; s/X/0/g' |
    sort -V |
    tail -1
}
