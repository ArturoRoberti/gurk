#################################################################################################################
################################################ File Processing ################################################
#################################################################################################################

# JSON
_json_lines() {
  local file=$1
  sed 's://.*$::; s:#.*$::' "$file" |
    jq -c 'to_entries[]'
}
_json_read() {
  local line
  if IFS= read -r line; then
    key=$(jq -r '.key' <<<"$line")
    if jq -e '.value | arrays' >/dev/null <<<"$line"; then
      # Populate Bash array
      mapfile -t value < <(jq -r '.value[]' <<<"$line")
    else
      # Scalar
      value=$(jq -r '.value' <<<"$line")
    fi
    return 0
  else
    return 1
  fi
}

# TXT
_txt_lines() {
  local file=$1
  while IFS= read -r line || [[ -n $line ]]; do
    # Trim + remove comments
    line="${line%%#*}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z $line ]] && continue
    echo "$line"
  done <"$file"
}
_txt_read() {
  if IFS= read -r line; then
    return 0
  else
    return 1
  fi
}

# Get file extension
_get_file_extension() {
  local file=$1
  local ext="${file##*.}"
  echo "${ext,,}"
}

# Interfaces
_lines() {
  local file=$1
  local ext=$(_get_file_extension "$file")

  case "$ext" in
    json | jsonc) _json_lines "$file" ;;
    txt) _txt_lines "$file" ;;
    *)
      echo "Unsupported file extension: $ext" >&2
      return 1
      ;;
  esac
}
_read() {
  local file=$1
  local ext=$(_get_file_extension "$file")
  case "$ext" in
    json | jsonc) _json_read ;;
    txt) _txt_read ;;
    *)
      return 1
      ;;
  esac
}

#################################################################################################################
############################################# Bash Array Processing #############################################
#################################################################################################################

# Extract array contents from either an array variable name or a list of arguments
# TODO: Remove?
_extract_array() {
  local elements=()

  # If a single argument is an array variable name, use its contents
  if (($# == 1)) && declare -p "$1" &>/dev/null && [[ "$(declare -p "$1")" =~ "declare -a" ]]; then
    local -n arr_ref=$1        # nameref to external array
    elements=("${arr_ref[@]}") # extract array contents
  else
    # Otherwise, treat all arguments as package names
    elements=("$@")
  fi

  if ((${#elements[@]} > 0)); then
    printf '%s\n' "${elements[@]}"
  fi
}

# Check if an array (indexed or associative) or scalar contains any of the specified values/keys (match case)
_contains() {
  local arr_name=$1
  local -n arr=$arr_name # nameref to array

  # Detect array type: "indexed" or "associative"
  local type=$(declare -p "$arr_name" 2>/dev/null)

  shift # Shift to get the needles
  if [[ $type =~ "declare -A" ]]; then
    # Associative array: check KEYS
    for needle in "$@"; do
      if [[ -v arr["$needle"] ]]; then
        return 0
      fi
    done
  else
    # Indexed array (or other scalar type): check VALUES
    for needle in "$@"; do
      for element in "${arr[@]}"; do
        if [[ $element == "$needle" ]]; then
          return 0
        fi
      done
    done
  fi

  return 1
}

_wait_dpkg() {
  : '
    Install packages with dpkg lock waiting to avoid conflicts.
    '
  sudo flock /var/lib/dpkg/lock-frontend "$@"
}

dpkg_install() {
  : '
    Install debian packages safely
    '
  _wait_dpkg sudo dpkg -i "$@"
}

apt_install() {
  : '
    Install apt packages safely
    '
  _wait_dpkg sudo apt-get install -y "$@"
}
