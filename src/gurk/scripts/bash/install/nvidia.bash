# TODO: Use "SYSTEM_INFO['simulate_hardware']" flag

_extract_table_rows() {
	: '
	Extract table rows from NVIDIA CUDA compatibility HTML page

	Args:
	  - html:	HTML content as a string
	Outputs:
	  Table rows as a string
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local html="$1"

	# Extract table info - NOTE: Title may change over time
	local xpath_selector="//caption[contains(., 'CUDA Toolkit and Corresponding Driver Versions')]/ancestor::table[1]//tr"
	xmllint --html --xpath "$xpath_selector" - 2>/dev/null <<<"$html" |
		tr '\n' ' ' |
		sed 's%</tr>%\n%g; s%<t[dh][^>]*>%%g; s%</t[dh]>%|%g; s/<[^>]*>//g; s/&#13;//g; s/&gt;/>/g; s/&nbsp;/ /g'
}

_parse_cuda_driver_map() {
	: '
	Parse table rows into a simple CUDA -> driver mapping

	Args:
	  - rows:	Table rows as a string
	Outputs:
	  CUDA to driver version mapping as "CUDA_version:driver_version" per line
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local rows="$1"
	awk -F'|' '{
		gsub(/^ +| +$/,"",$1); gsub(/^ +| +$/,"",$2);
		if(($1 ~ /GA/ || $1 ~ /Update/) && $2!="") print $1 ":" $2
	}' <<<"$rows"
}

_ver2num() {
	: '
	Convert version string "X.Y.Z" to a comparable number by padding each component.

	Args:
	  - v:			Version string (e.g. "535.54.03")
	  - max_major:	Maximum width for major version
	  - max_minor:	Maximum width for minor version
	  - max_patch:	Maximum width for patch version
	Outputs:
	  Comparable version number as a string
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local v="$1"
	local max_major="$2"
	local max_minor="$3"
	local max_patch="$4"
	local a
	IFS='.' read -r -a a <<<"$v"
	a[0]=$((10#${a[0]:-0}))
	a[1]=$((10#${a[1]:-0}))
	a[2]=$((10#${a[2]:-0}))

	# Pad each component to max width using printf
	printf -v padded "%0*d%0*d%0*d" "$max_major" "${a[0]}" "$max_minor" "${a[1]}" "$max_patch" "${a[2]}"
	echo "$padded"
}

_clean_version() {
	: '
	Clean version string by removing comparison operators and padding missing patch.

	Args:
	  - v:	Version string (e.g. ">=535.54", "<=460.32.03")
	Outputs:
	  Cleaned version string (e.g. "535.54.0", "460.32.03")
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local v="$1"
	v="${v//>=/}"
	v="${v//>/}"
	v="${v//<=/}"
	v="${v//</}"
	[[ "$v" =~ ^[0-9]+\.[0-9]+$ ]] && v="$v.0"
	echo "$v"
}

_get_max_version_widths() {
	: '
	Determine the maximum width of major, minor, patch in a list of versions

	Args:
	  - versions:	List of versions as "CUDA_version:driver_version" per line
	Outputs:
	  Maximum widths of major, minor, patch as three space-separated numbers
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local versions="$1"
	local max_major=0 max_minor=0 max_patch=0
	local major minor patch

	while IFS=: read -r _ req_ver; do
		req_ver=$(_clean_version "$req_ver")
		IFS='.' read -r major minor patch <<<"$req_ver"
		major=$(echo "$major" | xargs)
		minor=$(echo "$minor" | xargs)
		patch=$(echo "$patch" | xargs)
		((${#major} > max_major)) && max_major=${#major}
		((${#minor} > max_minor)) && max_minor=${#minor}
		((${#patch} > max_patch)) && max_patch=${#patch}
	done <<<"$versions"

	echo "$max_major $max_minor $max_patch"
}

_find_best_cuda() {
	: '
	Find the newest compatible CUDA for a given driver

	Args:
	  - drv_ver:	NVIDIA driver version string (e.g. "535.54.03")
	  - map:		CUDA to driver version mapping as "CUDA_version:driver_version" per line
	Outputs:
	  Best matching CUDA and driver version as "CUDA_version:driver_version"
	Returns:
	  0 if found, 1 otherwise
	'
	local drv_ver="$1"
	local map="$2"
	local best=""

	# Compute max widths from the map
	read max_major max_minor max_patch <<<"$(_get_max_version_widths "$map")"
	local drv_num
	drv_num=$(_ver2num "$drv_ver" "$max_major" "$max_minor" "$max_patch")

	while IFS=: read -r cuda_ver req_ver; do
		cuda_ver=$(echo "$cuda_ver" | xargs)
		req_ver=$(echo "$req_ver" | xargs)
		req_ver=$(_clean_version "$req_ver")
		local req_num=$(_ver2num "$req_ver" "$max_major" "$max_minor" "$max_patch")
		if ((req_num <= drv_num)); then
			best="$cuda_ver:$req_ver"
			break
		fi
	done <<<"$map"

	[[ -z "$best" ]] && return 1

	echo "$best"
}

_detect_recommended_driver() {
	: '
	Detect the recommended NVIDIA driver using ubuntu-drivers.

	Args:
	  None
	Outputs:
	  Recommended NVIDIA driver package name (e.g. "nvidia-driver-535")
	Returns:
	  0 if found, 1 otherwise
	'
	local drv
	drv=$(ubuntu-drivers devices 2>/dev/null | awk '/recommended/ {print $3; exit}')
	[[ -z "$drv" ]] && return 1

	echo "$drv"
}

_get_candidate_driver_version() {
	: '
	Get the driver version from a given NVIDIA driver package name.

	Args:
	  - driver_pkg:	NVIDIA driver package name (e.g. "nvidia-driver-535")
	Outputs:
	  Driver version string (e.g. "535.54.03")
	Returns:
	  0 if found, 1 otherwise
	'
	local driver_pkg="$1"
	local version
	version=$(apt show "$driver_pkg" 2>/dev/null | awk -F': ' '/^Version:/ {print $2; exit}')
	[[ -z "$version" ]] && return 1

	# Extract numeric driver version (e.g., 535.54.03)
	version=$(echo "$version" | grep -oP '^[0-9]+(\.[0-9]+){1,2}' | head -1)
	[[ -z "$version" ]] && return 1

	echo "$version"
}

_add_graphics_drivers_ppa() {
	: '
	Add graphics-drivers PPA for latest NVIDIA drivers. Optionally prioritize it above NVIDIA driver packages.

	Args:
	  - prime_select:	Whether to prioritize graphics-drivers PPA for NVIDIA driver packages (default: false)
	Outputs:
	  Log messages indicating the current progress
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local prime_select="${1:-false}"

	if ! grep -R "graphics-drivers/ppa" /etc/apt/sources.list /etc/apt/sources.list.d/ >/dev/null; then
		# Add PPA
		sudo add-apt-repository -y ppa:graphics-drivers/ppa
	fi

	if [[ "$prime_select" == true ]]; then
		# TODO: May not work - in that case remove /etc/apt/.../cuda* files instead (pin and list)
		# Prioritize graphics-drivers PPA for NVIDIA driver packages (over CUDA repo)
		sudo tee /etc/apt/preferences.d/gurk-nvidia-driver-pin >/dev/null <<-'EOF'
			Package: nvidia-driver-* nvidia-dkms-* nvidia-kernel-source-* nvidia-kernel-common-* libnvidia-* \
			nvidia-compute-utils-* nvidia-utils-* xserver-xorg-video-nvidia-* nvidia-prime nvidia-settings
			Pin: release o=LP-PPA-graphics-drivers
			Pin-Priority: 601
		EOF
	fi

	# Update apt after configuring repositories
	sudo apt-get update
}

_install_nvidia_driver() {
	: '
	(Internal) Install NVIDIA Driver

	Args:
	  - driver_version:	NVIDIA driver package name (e.g. "nvidia-driver-535")
	  - prime_select:	Whether to prioritize NVIDIA GPU via prime-select (default: false)
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful, 1 otherwise
	'
	local driver_version="$1"
	local prime_select="${2:-false}"

	#Install Requirement(s)
	apt_install mokutil
	if [[ "$prime_select" == true ]]; then
		apt_install nvidia-prime
	fi

	# Check if secure boot is enabled
	output=$(mokutil --sb-state 2>/dev/null)
	if echo "$output" | grep -q "enabled"; then
		log_step "Aborting NVIDIA driver installation, as Secure Boot is ENABLED. Please disable Secure Boot via your BIOS menu and try again." true
		return 1
	elif ! echo "$output" | grep -q "disabled"; then
		log_step "Could not determine Secure Boot state - assuming it is disabled."
	fi

	# Install Driver
	apt_install "$driver_version"

	# Prioritizing NVIDIA GPU
	if [[ "$prime_select" == true ]]; then
		sudo prime-select nvidia
	fi
}

install_nvidia_driver() {
	: '
	Manager NVIDIA Driver PPAs and install NVIDIA Driver.

	WARNING: This will install the requested or recommended NVIDIA driver,
			 replacing any existing (cuda-repository) driver installation.

	Args:
	  - Configuration Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Check if NVIDIA Driver is already installed
	if check_install_nvidia_driver && [[ "$FORCE" == false ]]; then
		# TODO: Check if version matches the recommended/requested one?
		# TODO: Check if prime-select is set (if requested)?
		log_step "NVIDIA Driver is already installed - Exiting"
		return 0
	fi

	# See if prime-select is requested
	local prime_select=false
	if _contains REMAINING_ARGS "--prime-select"; then
		prime_select=true
	fi
	_add_graphics_drivers_ppa "$prime_select"

	# (STEP) Determining requested NVIDIA driver
	driver_version=""
	if _contains REMAINING_ARGS "recommended"; then
		# (1st Priority) Use recommended driver
		driver_version=$(_detect_recommended_driver)
	elif _contains REMAINING_ARGS "latest"; then
		# (2nd Priority) Use latest available driver
		search_results=$(apt-cache search '^nvidia-driver-[0-9]+')
		if ! _contains REMAINING_ARGS "--include-server"; then
			# Filter out server drivers if not requested
			search_results=$(echo "$search_results" | grep -v 'server')
		fi
		if ! _contains REMAINING_ARGS "--include-open"; then
			# Filter out open drivers if not requested
			search_results=$(echo "$search_results" | grep -v 'open')
		fi
		driver_version=$(echo "$search_results" | awk '{print $1}' | sort -V | tail -n1)
	else
		# (Last Priority) Use specified driver
		for driver in "${REMAINING_ARGS[@]}"; do
			if [[ "$driver" == nvidia-driver-* ]]; then
				driver_version="$driver"
				break
			fi
		done
	fi
	if [[ -z "$driver_version" ]]; then
		log_step "No (valid) NVIDIA driver specified (recommended, latest, nvidia-driver-*)" true
		return 1
	fi

	# (STEP) Installing Driver: $driver_version
	_install_nvidia_driver "$driver_version" "$prime_select"
}

_configure_apt_repositories_cuda() {
	: '
	Configure apt repositories for CUDA installation.

	Args:
	  None
	Outputs:
	  Log messages indicating the current progress
	Returns:
	  0 (unless an unexpected error occurs)
	'
	# Remove graphics-drivers PPA prioritization (if previously added via "install-nvidia-driver" task)
	if [[ -f "/etc/apt/preferences.d/gurk-nvidia-driver-pin" ]]; then
		sudo rm -f /etc/apt/preferences.d/gurk-nvidia-driver-pin
	fi

	# Get cuda repository pin
	local distro="${SYSTEM_INFO[name]}$(remove_dots "${SYSTEM_INFO[version]}")"
	local distro_path="${distro}/${SYSTEM_INFO[kernel]}"
	local base_url="https://developer.download.nvidia.com/compute/cuda/repos/${distro_path}"
	local tmpfile=$(mktemp --suffix=".pin")
	wget "${base_url}/cuda-${distro}.pin" -O "${tmpfile}"
	sudo mv "${tmpfile}" /etc/apt/preferences.d/cuda-repository-pin-600

	# Add CUDA GPG keyring - TODO: Update so that the .gpg file is known?
	local cuda_keyring_deb=$(curl -s "${base_url}/" |
		grep -oP 'cuda-keyring_[0-9.]+-[0-9]+_all\.deb' |
		sort -V | tail -n1)
	local tmpfile=$(mktemp --suffix=".deb")
	wget -nv "${base_url}/${cuda_keyring_deb}" -O "${tmpfile}"
	dpkg_install "${tmpfile}"
	rm "${tmpfile}"

	# Add CUDA apt repository
	sudo tee /etc/apt/sources.list.d/cuda.list >/dev/null <<-EOF
		deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] ${base_url}/ /
	EOF

	# Update apt after configuring repositories
	sudo apt-get update
}

_install_cuda() {
	: '
	(Internal) Install CUDA Toolkit

	Args:
	  - cuda_name:	CUDA package name (e.g. "cuda-11-8")
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful, 1 otherwise
	'
	local cuda_name="$1"
	local cuda_major_minor=$(echo "$cuda_name" | grep -oP '\d+\.\d+')
	local cuda_major=$(echo "$cuda_major_minor" | cut -d. -f1)
	local cuda_minor=$(echo "$cuda_major_minor" | cut -d. -f2)
	local cuda_pkg="cuda-${cuda_major}-${cuda_minor}"
	sudo apt-get update && apt_install "$cuda_pkg"

	# Update environment variables
	write_marked 'export PATH=/usr/local/cuda/bin:$PATH' "${HOME}/.bashrc" true
	write_marked 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' "${HOME}/.bashrc" true
}

install_cuda() {
	: '
	Install NVIDIA Driver and CUDA Toolkit.

	WARNING: This will install the recommended NVIDIA driver from the CUDA repository,
			 replacing any existing driver installation and removing any prime-select
			 configuration that may exist on systems with hybrid graphics (e.g. most laptops).

	Args:
	  - Configuration Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Check if CUDA is already installed
	if check_install_cuda && [[ "$FORCE" == false ]]; then
		if ! check_install_nvidia_driver; then
			log_step "CUDA is already installed, but a (compatible) NVIDIA Driver is missing - Installing again with recommended driver"
		else
			# TODO: Check if driver is compatible with installed CUDA
			log_step "CUDA and NVIDIA Driver are already installed - Exiting"
			return 0
		fi
	fi

	# Check GCC version compatibility - TODO: Do steps automatically?
	if ! check_gcc_version; then
		log_step "ERROR: Incompatibility between current default GCC version and kernel CC version detected (see previous logs)." true
		echo "Consider using the following to install the correct version:"
		echo "sudo apt update && sudo apt install gcc-<kernel-major-version> g++-<kernel-major-version>"
		echo "sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-<CURRENT-GCC-MAJOR-VERSION> 10"
		echo "sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-<kernel-major-version> 20"
		echo "Later, update-alternatives can be used to revert to the previous GCC version (if desired). You can also use 'sudo update-alternatives --config gc' to switch."
		return 1
	fi

	# (STEP) Installing Requirement(s)
	apt_install pciutils curl software-properties-common libxml2-utils ubuntu-drivers-common

	# (STEP) Detecting GPU
	if ! lspci | grep -i VGA | grep -iq nvidia; then
		log_step "No NVIDIA GPU detected - skipping CUDA installation"
		return 0
	fi

	# (STEP) Retrieving CUDA → driver mapping from NVIDIA webpage
	local html_page=$(curl -sS "https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html")
	local table_rows=$(_extract_table_rows "$html_page")
	local cuda_driver_map=$(_parse_cuda_driver_map "$table_rows")

	# (STEP) Detecting recommended NVIDIA driver
	_configure_apt_repositories_cuda
	local recommended_driver=$(_detect_recommended_driver)
	local candidate_driver=$(_get_candidate_driver_version "$recommended_driver")

	# (STEP) Parsing CUDA name and version
	local best_cuda=$(_find_best_cuda "$candidate_driver" "$cuda_driver_map")
	local cuda_name=$(cut -d':' -f1 <<<"$best_cuda")
	local cuda_version=$(cut -d':' -f2 <<<"$best_cuda")

	echo "Recommended driver: $recommended_driver"
	echo "Recommended CUDA  : $cuda_name"

	# (STEP) Installing Driver: $recommended_driver (this may take a while)...
	_install_nvidia_driver "$recommended_driver" false

	# Verify driver installation
	check_install_nvidia_driver

	# (STEP) Installing CUDA: $cuda_name (this may take a while)...
	_install_cuda "$cuda_name"

	# Verify installation
	check_install_cuda
}
