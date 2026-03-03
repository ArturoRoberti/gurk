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

check_configure_bashrc() {
	: "
	Check if the ~/.bashrc has been configured with the custom lines.

	Args:
	  None
	Outputs:
	  Log messages indicating the current progress
	Returns:
	  0 if configured, 1 otherwise
	"
	if markers_exist "$HOME/.bashrc"; then
		log_step "~/.bashrc is already configured"
		return 0
	else
		log_step "~/.bashrc is not configured"
		return 1
	fi
}
