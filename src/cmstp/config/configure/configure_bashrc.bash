# Sourcing util
_source_if_exists() {
	[ -f "$1" ] && source "$1"
}

# Custom bash aliases and commands/scripts
_source_if_exists ${HOME}/.cmds/aliases.bash
export PATH=${PATH}:${HOME}/.cmds

# Colors
color() {
	echo "\[\e[$1m\]"
}
NC=$(color 0)
## Normal
RED=$(color 0\;31)
GREEN=$(color 0\;32)
ORANGE=$(color 0\;33)
BLUE=$(color 0\;34)
## Bold
BOLD_RED=$(color 1\;31)
BOLD_GREEN=$(color 1\;32)
BOLD_ORANGE=$(color 1\;33)
BOLD_BLUE=$(color 1\;34)

# Shell coloring
_parse_git_branch() {
	git branch 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
}
export PS1="${BOLD_GREEN}\u@\h${NC}:${BOLD_BLUE}\w${BOLD_RED}\$(_parse_git_branch)${NC}\$ "
