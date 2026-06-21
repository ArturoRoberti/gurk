install_claude_code() {
	: "
	Install Claude Code

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

	# Check if Claude Code is already installed
	if check_install_claude_code && [[ "$FORCE" == false ]]; then
		log_step "Claude Code is already installed - Exiting"
		return 0
	fi

	# Check OS type
	if [[ "${SYSTEM_INFO[type]}" != "linux" && "${SYSTEM_INFO[type]}" != "darwin" && "${SYSTEM_INFO[type]}" != "windows" ]]; then
		log_step "Unsupported OS type for Claude Code: ${SYSTEM_INFO[type]}" true
		return 1
	fi

	# Handle based on OS type
	if [[ "${SYSTEM_INFO[type]}" == "linux" || "${SYSTEM_INFO[type]}" == "darwin" ]]; then
		# (STEP) Installing Requirement(s)
		apt_install curl

		# (STEP) Installing Claude Code
		curl -fsSL https://claude.ai/install.sh | bash

	elif [[ "${SYSTEM_INFO[type]}" == "windows" ]]; then
		# POWERSHELL: 	irm https://claude.ai/install.ps1 | iex
		# CMD: 			curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
		log_step "Windows installation for Claude Code is not supported yet. Please see https://code.claude.com/docs/en/quickstart" true
		return 1
	fi

	# Verify installation
	check_install_claude_code
}

install_codex() {
	: "
	Install Codex

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

	# Check if Codex is already installed
	if check_install_codex && [[ "$FORCE" == false ]]; then
		log_step "Codex is already installed - Exiting"
		return 0
	fi

	# Check OS type
	if [[ "${SYSTEM_INFO[type]}" != "linux" && "${SYSTEM_INFO[type]}" != "darwin" && "${SYSTEM_INFO[type]}" != "windows" ]]; then
		log_step "Unsupported OS type for Codex: ${SYSTEM_INFO[type]}" true
		return 1
	fi

	# Handle based on OS type
	if [[ "${SYSTEM_INFO[type]}" == "linux" || "${SYSTEM_INFO[type]}" == "darwin" ]]; then
		# Handle based on installation method
		if [[ "$AGENTS_CODEX_INSTALLATION_METHOD" == "curl" ]]; then
			# (STEP) Installing Requirement(s)
			apt_install curl

			# (STEP) Installing Codex
			curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh

		elif [[ "$AGENTS_CODEX_INSTALLATION_METHOD" == "npm" ]]; then
			# (STEP) Installing Requirement(s)
			apt_install nodejs npm

			# (STEP) Installing Codex
			npm install -g @openai/codex

		else
			# POWERSHELL: 	$env:CODEX_NON_INTERACTIVE=1; irm https://chatgpt.com/codex/install.ps1 | iex
			log_step "Unsupported installation method for Codex: $AGENTS_CODEX_INSTALLATION_METHOD" true
			return 1
		fi
	elif [[ "${SYSTEM_INFO[type]}" == "windows" ]]; then
		log_step "Windows installation for Codex is not supported yet. Please see https://openai.com/blog/openai-codex" true
		return 1
	fi

	# Verify installation
	check_install_codex
}

install_gemini_cli() {
	: "
	Install Gemini CLI

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

	# Check if Gemini CLI is already installed
	if check_install_gemini_cli && [[ "$FORCE" == false ]]; then
		log_step "Gemini CLI is already installed - Exiting"
		return 0
	fi

	# Check OS type
	if [[ "${SYSTEM_INFO[type]}" != "linux" && "${SYSTEM_INFO[type]}" != "darwin" ]]; then
		log_step "Unsupported OS type for Gemini CLI: ${SYSTEM_INFO[type]}" true
		return 1
	fi

	# Handle based on installation method
	if [[ "$AGENTS_GEMINI_CLI_INSTALLATION_METHOD" == "npm" ]]; then
		# (STEP) Installing Requirement(s)
		apt_install nodejs npm

		# (STEP) Installing Gemini CLI
		npm install -g @google/gemini-cli

	elif [[ "$AGENTS_GEMINI_CLI_INSTALLATION_METHOD" == "conda" ]]; then
		local env_name="gemini_env"
		# (STEP) Creating Gemini CLI Conda environment: $env_name
		bash -ic "conda create -y -n $env_name -c conda-forge nodejs"

		# (STEP) Installing Gemini CLI in Conda environment: $env_name
		bash -ic "conda run -n $env_name npm install -g @google/gemini-cli"

	else
		log_step "Unsupported installation method for Gemini CLI: $AGENTS_GEMINI_CLI_INSTALLATION_METHOD" true
		return 1
	fi

	# Verify installation
	check_install_gemini_cli
}

install_copilot_cli() {
	: "
	Install Copilot CLI

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and installation outputs
	Returns:
	  0 if successful (or already installed), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

	# Check if Copilot CLI is already installed
	if check_install_copilot_cli && [[ "$FORCE" == false ]]; then
		log_step "Copilot CLI is already installed - Exiting"
		return 0
	fi

	# Check OS type
	if [[ "${SYSTEM_INFO[type]}" != "linux" && "${SYSTEM_INFO[type]}" != "darwin" ]]; then
		log_step "Unsupported OS type for Copilot CLI: ${SYSTEM_INFO[type]}" true
		return 1
	fi

	# Handle based on installation method
	if [[ "$AGENTS_COPILOT_CLI_INSTALLATION_METHOD" == "curl" ]]; then
		# (STEP) Installing Requirement(s)
		apt_install curl

		# (STEP) Installing Copilot CLI
		curl -fsSL https://gh.io/copilot-install | bash

	elif [[ "$AGENTS_COPILOT_CLI_INSTALLATION_METHOD" == "npm" ]]; then
		# (STEP) Installing Requirement(s)
		apt_install nodejs npm

		# (STEP) Installing Copilot CLI
		npm install -g @github/copilot

	else
		log_step "Unsupported installation method for Copilot CLI: $AGENTS_COPILOT_CLI_INSTALLATION_METHOD" true
		return 1
	fi

	# Verify installation
	check_install_copilot_cli
}
