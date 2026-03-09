source "$(dirname "${BASH_SOURCE[0]}")/checks.bash"

install_vscode() {
	: "
	Install VSCode from source

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

	# Check if VSCode is already installed
	if check_install_vscode && [[ "$FORCE" == false ]]; then
		log_step "VSCode is already installed - Exiting"
		return 0
	fi

	# (STEP) Installing Requirement(s)
	apt_install apt-transport-https wget

	# (STEP) Adding VSCode APT Repository
	local gpg_file="/usr/share/keyrings/microsoft.gpg"
	wget -qO- https://packages.microsoft.com/keys/microsoft.asc \
 	 | sudo gpg --dearmor \
 	 | sudo tee $gpg_file >/dev/null
	echo "deb [arch=${SYSTEM_INFO[arch]} signed-by=$gpg_file] https://packages.microsoft.com/repos/code stable main" \
	  | sudo tee /etc/apt/sources.list.d/vscode.list
	sudo apt-get update

	# (STEP) Installing VSCode
	apt_install code

	# Verify installation
	check_install_vscode
}
