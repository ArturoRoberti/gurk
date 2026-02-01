check_install_vscode() {
	: "
	Check if Visual Studio Code is installed.

	Args:
	  None
	Outputs:
	  Path to the VSCode executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	"
	local vscode_path=$(command -v code)
	if [ -n "$vscode_path" ]; then
		echo "$vscode_path"
		return 0
	else
		return 1
	fi
}
