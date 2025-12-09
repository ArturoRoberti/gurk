log_step() {
  : '
    Log a step message with optional progress indicator.
    Args:
    $1 - message (string)
    $2 - progress (boolean, default: false)
    '
  local message="$1"
  local progress="${2:-false}"

  if [ "$progress" == "true" ]; then
    echo -e "\n__STEP__: $message"
  else
    echo -e "\n__STEP_NO_PROGRESS__: $message"
  fi
}

# TODO: Use this in "log_to_file". Maybe have extra arg there to enable/disable existing marker removal
marker_in_file() {
  : '
    Check if a CMSTP marker exists in a logfile.
    Args:
      $1 - logfile (string)
      $2 - marker (string)
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
      $1 - message (string or filepath)
      $2 - logfile (string)
      $3 - marker (string)
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
      $1 - logfile (string)
      $2 - marker (string)
    '
  local logfile="$1"
  local marker="$2"

  # Use sed to delete from CMSTP START <marker> to CMSTP END <marker>
  sed -i "/#* CMSTP START[[:space:]]\+$marker #*/,/#* CMSTP END[[:space:]]\+$marker #*/d" "$logfile"
}
