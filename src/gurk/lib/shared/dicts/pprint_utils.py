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
def _combine_lines(lines: list[str]) -> str:
    """
    Combine a list of lines into a single string with normalized newlines.

    Strips trailing newlines from each line, joins with single newline separators,
    and ensures exactly one trailing newline at the end.

    :param lines: List of line strings (may have trailing newlines)
    :type lines: list[str]
    :return: Combined string with single trailing newline
    :rtype: str
    """
    out = "\n".join(line.rstrip("\n") for line in lines)
    return out + ("\n" if not out.endswith("\n") else "")
