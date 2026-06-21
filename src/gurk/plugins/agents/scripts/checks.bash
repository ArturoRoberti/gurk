check_install_claude_code() {
	: "
	Check if Claude Code is installed.

	Args:
	  None
	Outputs:
	  Path to the Claude Code executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local claude_code_path=$(command -v claude)
	if [ -n "$claude_code_path" ]; then
		echo "$claude_code_path"
		return 0
	else
		return 1
	fi
}

check_install_codex() {
	: "
	Check if Codex is installed.

	Args:
	  None
	Outputs:
	  Path to the Codex executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local codex_path=$(command -v codex)
	if [ -n "$codex_path" ]; then
		echo "$codex_path"
		return 0
	else
		return 1
	fi
}

check_install_gemini_cli() {
	: "
	Check if Gemini CLI is installed.

	Args:
	  None
	Outputs:
	  Path to the Gemini CLI executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local gemini_cli_path=$(command -v gemini)
	if [ -n "$gemini_cli_path" ]; then
		echo "$gemini_cli_path"
		return 0
	else
		return 1
	fi
}

check_install_copilot_cli() {
	: "
	Check if Copilot CLI is installed.

	Args:
	  None
	Outputs:
	  Path to the Copilot CLI executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local copilot_cli_path=$(command -v copilot)
	if [ -n "$copilot_cli_path" ]; then
		echo "$copilot_cli_path"
		return 0
	else
		return 1
	fi
}
