_get_supported_ros_distros() {
	: '
	Get a list of supported ROS distros for the current OS.
	Returns an array of supported ROS distro codenames.

	Args:
	  None
	Outputs:
	  List of supported ROS distro codenames
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local supported_ros_distros
	supported_ros_distros=($(apt-cache search ros- | grep -E '^ros-[a-z]+-desktop-full' | awk '{print $1}' | sed 's/^ros-//;s/-desktop-full$//' | tr '\n' ' '))
	printf "%s\n" "${supported_ros_distros[@]}"
}

_get_latest_ros_distro() {
	: '
	Get the latest ROS distro codename from the official ROS releases page.
	If --include-future is provided in REMAINING_ARGS, future distros will also be considered.
	Returns the codename of the latest ROS distro.

	Args:
	  None
	Outputs:
	  Latest ROS distro codename
	Returns:
	  0 (unless an unexpected error occurs)
	'
	local include_future=false
	local url="https://docs.ros.org/en/rolling/Releases.html"
	local rows best_name best_ts ts eol name cls codename lc_eol

	# Use your provided check for --include-future
	if _contains REMAINING_ARGS "--include-future"; then
		include_future=true
	fi

	# Fetch and extract table rows
	rows=$(curl -fsSL "$url" |
		perl -MHTML::Entities -0777 -ne '
	  while (/<table[^>]*class="([^"]*distros[^"]*)"[^>]*>(.*?)<\/table>/gis) {
		my ($cls,$tbl) = ($1,$2);
		while ($tbl =~ /<tr[^>]*>(.*?)<\/tr>/gis) {
		  my $tr = $1;
		  my @td = ($tr =~ /<td[^>]*>(.*?)<\/td>/gis);
		  next unless @td >= 4;
		  my $name = $td[0]; my $eol = $td[3];
		  $name =~ s/<[^>]+>//g; $eol =~ s/<[^>]+>//g;
		  decode_entities($name); decode_entities($eol);
		  $name =~ s/^\s+|\s+$//g; $eol =~ s/^\s+|\s+$//g;
		  print "$name\t$eol\t$cls\n";
		}
	  }
	')

	# Get supported distros for filtering
	local supported_ros_distros
	supported_ros_distros=($(_get_supported_ros_distros | tr '\n' ' '))

	best_name=""
	best_ts=0
	while IFS=$'\t' read -r name eol cls; do
		# codename: first word, lowercase, non-alnum -> '-'
		codename=$(printf "%s" "${name%% *}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')

		# skip unsupported distros
		if ! _contains supported_ros_distros "$codename"; then
			continue
		fi

		# skip empty / placeholder EOLs
		lc_eol=${eol,,}
		case "$lc_eol" in
			tbd | n/a | -) continue ;;
		esac

		# skip future distros if not including them
		if [[ "$include_future" == false && "$cls" == *future-distros* ]]; then
			continue
		fi

		ts=""
		# full date: "August 14, 2024"
		if [[ $eol =~ ^[A-Za-z]+[[:space:]]+[0-9]{1,2},[[:space:]]*[0-9]{4}$ ]]; then
			ts=$(date -d "$eol" +%s 2>/dev/null || true)
		# month + year: "Aug 2024" or "August 2024" -> last day of month
		elif [[ $eol =~ ^[A-Za-z]{3,}[[:space:]]+[0-9]{4}$ ]]; then
			ts=$(date -d "1 $eol +1 month -1 day" +%s 2>/dev/null || true)
		# just a year -> Dec 31
		elif [[ $eol =~ ([0-9]{4}) ]]; then
			local year=${BASH_REMATCH[1]}
			ts=$(date -d "31 Dec $year" +%s 2>/dev/null || true)
		fi

		[[ -z "$ts" ]] && continue

		if ((ts > best_ts)); then
			best_ts=$ts
			best_name="$name"
		fi
	done <<<"$rows"

	[[ -z "$best_name" ]] && return 1

	# codename: first word, lowercase, non-alnum -> '-'
	codename=$(printf "%s" "${best_name%% *}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')
	printf "%s\n" "$codename"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	: '
	Install ROS distros.

	NOTE: This can only install ROS distros officially supported by the host OS.
		  If any other distros are needed, consider using ROS docker images.
		  See 'install-docker-images' task for more details on ROS docker images.
		  You can (usually) find more info about supported OSs at https://docs.ros.org/en/<distro>/Installation.html

	Args:
	  - Configuration Args
	  - DISTRO...:   List of ROS distro codenames to install (e.g. "noetic", "foxy", "galactic").
					 Use "latest" to install the latest supported ROS distro.
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	'
	# Parse config args
	get_config_args "$@"

	# Check if ROS is already installed
	if check_install_ros && [[ "$FORCE" == false ]]; then
		log_step "ROS is already installed - Exiting"
		return 0
	fi

	# (STEP) Installing Requirement(s)
	apt_install curl software-properties-common

	# (STEP) Ensuring 'universe' repository is enabled
	sudo add-apt-repository -y universe

	# (STEP) Getting latest ros-apt-source release
	ros_apt_source_intpath="ros-infrastructure/ros-apt-source/releases"
	ros_apt_source_version=$(curl -s https://api.github.com/repos/${ros_apt_source_intpath}/latest | grep -F "tag_name" | awk -F\" '{print $4}')
	tmpfile=$(mktemp --suffix=".deb")
	curl -L -o "${tmpfile}" \
		"https://github.com/${ros_apt_source_intpath}/download/${ros_apt_source_version}/ros2-apt-source_${ros_apt_source_version}.${SYSTEM_INFO[codename]}_all.deb"
	dpkg_install "${tmpfile}"
	sudo apt-get update
	rm "${tmpfile}"

	# (STEP) Preparing distros to install
	supported_ros_distros=($(_get_supported_ros_distros | tr '\n' ' '))
	DISTROS=()
	for distro in "${REMAINING_ARGS[@]}"; do
		if [[ "$distro" == "latest" ]]; then
			DISTROS+=($(_get_latest_ros_distro))
			log_step "Detected latest supported ROS distro: ${DISTROS[-1]}"
		elif ! _contains supported_ros_distros "$distro"; then
			log_step "Skipping unsupported ROS distro: $distro"
			continue
		else
			# Include normal distro
			DISTROS+=("$distro")
		fi
	done

	# (STEP) Installing ROS distro(s)
	for distro in "${DISTROS[@]}"; do
		log_step "Installing ROS distro: $distro"
		apt_install "ros-${distro}-desktop-full"
	done

	# (STEP) Installing ROS development tools
	apt_install ros-dev-tools

	# Verify installation
	check_install_ros
fi
