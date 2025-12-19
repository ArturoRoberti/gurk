log_step() {
  : '
    Log a step message without advancing progress.

    Args:
      - message:   Message to log.
      - warning:   Whether or not this is a warning (default: false).
    Outputs:
      Log messages indicating the current progress
    Returns:
      0 (unless an unexpected error occurs)
    '
  local message="$1"
  local warning="${2:-false}"

  local step_type="STEP_NO_PROGRESS"
  if [ "$warning" = true ]; then
    step_type+="_WARNING"
  fi
  echo -e "\n__${step_type}__: $message"
}

# TODO: Use this in "log_to_file". Maybe have extra arg there to enable/disable existing marker removal
marker_in_file() {
  : '
    Check if a CMSTP marker exists in a logfile.

    Args:
      - logfile:   Path to the logfile.
      - marker:    Marker string to search for.
    Outputs:
      None
    Returns:
      0 if marker found, 1 otherwise
    '
  local logfile="$1"
  local marker="$2"

  if grep -qE "CMSTP START[[:space:]]+$marker" "$logfile"; then
    return 0 # marker found
  else
    return 1 # marker not found
  fi
}

log_to_file() {
  : '
    Log a message or file content to a logfile, wrapped with start and end markers.

    Args:
      - message:   Message string or path to file to log.
      - logfile:   Path to the logfile.
      - marker:    Marker string to wrap the logged content.
    Outputs:
      None
    Returns:
      0 (unless an unexpected error occurs)
    '
  local message="$1"
  local logfile="$2"
  local marker="$3"

  # Generate the hash string
  local hashes=$(printf '#%.0s' $(seq 1 10))

  # Write start marker
  echo -e "\n${hashes} CMSTP START ${marker} ${hashes}\n" >>"$logfile"

  # Write message
  if [ -f "$message" ]; then
    # File
    cat "$message" >>"$logfile"
  else
    # String
    echo -e "$message" >>"$logfile"
  fi

  # Write end marker
  echo -e "\n${hashes} CMSTP END ${marker} ${hashes}" >>"$logfile"
}

# TODO: Adapt to more than just CMSTP markers (?), e.g. loki shell markers
remove_marker_from_file() {
  : '
    Remove all sections wrapped by a specific CMSTP marker from a logfile.

    Args:
      - logfile:   Path to the logfile.
      - marker:    Marker string to remove.
    Outputs:
      None
    Returns:
      0 (unless an unexpected error occurs)
    '
  local logfile="$1"
  local marker="$2"

  # Use sed to delete from CMSTP START <marker> to CMSTP END <marker>
  sed -i "/#* CMSTP START[[:space:]]\+$marker #*/,/#* CMSTP END[[:space:]]\+$marker #*/d" "$logfile"
}
