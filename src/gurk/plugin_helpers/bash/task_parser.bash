#!/usr/bin/env bash

# GURK: This inspired by argparse-bash, found at:
# https://github.com/nhoffman/argparse-bash
# MIT License - Copyright (c) 2015 Noah Hoffman

parse_task_args() {
	: "
    Parse task arguments using the GurkArgumentParser from Python.

	Args:
	  - Task name (str)
      - Remaining Args
	Outputs:
	  None
	Returns:
	  0 if successfully parsed, 1 otherwise
	"
	local args="[$(printf "'%s'," "$@" | sed 's/,$//')]" # Python list syntax
	local argparser=$(mktemp 2>/dev/null || mktemp -t argparser)
	cat >>"$argparser" <<EOF
import sys
from gurk import parse_task_args

args = parse_task_args(${args})
for arg in [a for a in dir(args) if not a.startswith('_')]:
    key = arg.upper()
    value = getattr(args, arg, None)
    if isinstance(value, dict):
        print(f"declare -gA \"{key}\"")

    if value is None:
        print('{0}="";'.format(key))
    elif isinstance(value, bool):
        print('{0}="{1}";'.format(key, 'true' if value else 'false'))
    elif isinstance(value, list):
        print('{0}=({1});'.format(key, ' '.join('"{0}"'.format(s) for s in value)))
    elif isinstance(value, dict):
        for k, v in value.items():
            print('{0}["{1}"]="{2}";'.format(key, k, v))
    else:
        print('{0}="{1}";'.format(key, value))
EOF

	# Define variables corresponding to the options if the args can be
	# parsed without errors; otherwise, print the text of the error message.
	if python3 "$argparser" &>/dev/null; then
		eval $(python3 "$argparser")
		retval=0
	else
		echo "Error parsing task arguments:" >&2
		python3 "$argparser"
		retval=1
	fi

	rm "$argparser"
	return $retval
}
