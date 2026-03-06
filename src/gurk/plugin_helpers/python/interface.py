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

from gurk.lib.utils import typecheck


@typecheck
def log_step(message: str, /, *, warning: bool = False) -> None:
    """
    Log a step message without advancing progress. Only to be used from within tasks.

    :param message: Message to log
    :type message: str
    :param warning: Whether or not this is a warning (default: false)
    :type warning: bool
    """
    step_type = "STEP_NO_PROGRESS"
    if warning:
        step_type += "_WARNING"
    print(f"\n__{step_type}__: {message}")
