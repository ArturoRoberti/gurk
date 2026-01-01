_install_container_toolkit() {
	: '
	Install NVIDIA Container Toolkit for use with Docker.

	Args:
	  None
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	'
	# Check if NVIDIA Container Toolkit is already installed
	if check_install_container_toolkit && [[ "$FORCE" == false ]]; then
		log_step "NVIDIA Container Toolkit is already installed - Skipping"
		return 0
	fi

	# Add NVIDIA GPG key
	log_step "Adding NVIDIA GPG key"
	local nvidia_gpg_file="/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
	curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey |
		sudo gpg --dearmor | sudo tee "$nvidia_gpg_file"

	# Add NVIDIA Container Toolkit apt repository
	log_step "Adding NVIDIA Container Toolkit apt repository"
	curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |
		sed "s#deb https://#deb [signed-by=$nvidia_gpg_file] https://#g" |
		sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
	sudo apt-get update

	# Install NVIDIA Container Toolkit
	log_step "Installing NVIDIA Container Toolkit"
	apt_install nvidia-container-toolkit

	# Configure Docker runtime
	log_step "Configuring Docker runtime"
	sudo nvidia-ctk runtime configure --runtime=docker
	sudo systemctl restart docker

	# Verify installation
	check_install_container_toolkit
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	: '
	Install Docker Engine and related components.
	'
	# Parse config args
	get_config_args "$@"

	# Check if Docker is already installed
	if check_install_docker && [[ "$FORCE" == false ]]; then
		log_step "Docker is already installed - Exiting"
		exit 0
	fi

	# (STEP) Installing Requirement(s)
	apt_install ca-certificates curl

	# Ensure keyrings directory exists
	sudo install -m 0755 -d /etc/apt/keyrings

	# (STEP) Adding Docker GPG key
	docker_gpg_file="/etc/apt/keyrings/docker.asc"
	docker_gpg_url="https://download.docker.com/${SYSTEM_INFO[type]}/${SYSTEM_INFO[name]}/gpg"
	sudo curl -fsSL "$docker_gpg_url" -o "$docker_gpg_file"
	sudo chmod a+r "$docker_gpg_file"

	# (STEP) Adding Docker apt repository
	echo "deb [arch=${SYSTEM_INFO[arch]} signed-by=$docker_gpg_file] \
	https://download.docker.com/${SYSTEM_INFO[type]}/${SYSTEM_INFO[name]} ${SYSTEM_INFO[codename]} stable" |
		sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
	sudo apt-get update

	# (STEP) Installing Docker
	apt_install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

	# Make sure Docker is running
	sudo systemctl start docker

	# Verify Docker installation
	check_install_docker

	# Enable Docker BuildKit
	write_marked "export DOCKER_BUILDKIT=1" "${HOME}/.bashrc"

	if _contains REMAINING_ARGS nvidia-container-toolkit; then
		# (STEP) Installing NVIDIA Container Toolkit
		_install_container_toolkit
	fi

	if _contains REMAINING_ARGS devcontainers-cli; then
		# (STEP) Installing DevContainers CLI
		apt_install npm nodejs
		sudo npm install -g @devcontainers/cli
	fi

	# TODO: Check. Seems to fail on first time (not when done manually - maybe use "bash -ic" ?)
	if _contains REMAINING_ARGS distrobox; then
		# (STEP) Installing Distrobox
		curl -s https://raw.githubusercontent.com/89luca89/distrobox/main/install | sudo sh
	fi
fi
