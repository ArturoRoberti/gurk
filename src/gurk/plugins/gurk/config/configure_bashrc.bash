# Colors
_shell_color() {
	printf '\e[%sm' "$1"
}
NC=$(_shell_color 0)
## Normal
RED=$(_shell_color '0;31')
GREEN=$(_shell_color '0;32')
ORANGE=$(_shell_color '0;33')
BLUE=$(_shell_color '0;34')
## Bold
BOLD_RED=$(_shell_color '1;31')
BOLD_GREEN=$(_shell_color '1;32')
BOLD_ORANGE=$(_shell_color '1;33')
BOLD_BLUE=$(_shell_color '1;34')

# Shell coloring
_git_ps1_safe() {
	if declare -F __git_ps1 >/dev/null 2>&1; then
		__git_ps1
	fi
}
_container_name() {
	if [ -n "$CONTAINER_NAME" ]; then
		printf '{%s} ' "$CONTAINER_NAME"
	elif [ -n "$CONTAINER_ID" ]; then
		printf '{%s} ' "$CONTAINER_ID"
	fi
}
_container_color() {
	if [ -n "$CONTAINER_NAME" ] || [ -n "$CONTAINER_ID" ]; then
		printf '%s' "$BOLD_ORANGE"
	else
		printf '%s' "$BOLD_GREEN"
	fi
}
export PS1="\$(_container_name)\[\$(_container_color)\]\u@\h\[$NC\]:\[$BOLD_BLUE\]\w\[$BOLD_RED\]\$(_git_ps1_safe)\[$NC\]\$ "
