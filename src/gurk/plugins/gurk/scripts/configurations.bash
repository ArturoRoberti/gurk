# Copyright 2026 Arturo Roberti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

source "$(dirname "${BASH_SOURCE[0]}")/checks.bash"

configure_bashrc() {
	: "
	Add custom lines to ~/.bashrc.

	Args:
	  - Task Args
	Outputs:
	  Log messages indicating the current progress and configuration outputs
	Returns:
	  0 if successful (or already configured), 1 otherwise
	"
	# Parse task args
	parse_task_args "$@"

	# Check if config file is provided
	if [ -z "$CONFIG_FILE" ]; then
		log_step "Skipping configuration of the ~/.bashrc, as no task config file is provided" true
		return 0
	fi

	# Append custom bashrc lines to ~/.bashrc
	local check_existing=true
	if [[ "$FORCE" == true ]]; then
		check_existing=false
	fi
	write_marked "$CONFIG_FILE" "$HOME/.bashrc" "$check_existing"

	# Verify configuration
	check_configure_bashrc
}
