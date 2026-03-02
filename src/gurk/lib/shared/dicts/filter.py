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

from typing import TypeVar

from pydantic import TypeAdapter

from gurk.lib.utils import typecheck

T = TypeVar("T")


@typecheck
def filter_typed_dict(dct: dict, tp: type[T]) -> T:
    """
    Filter a dictionary to only include keys that are defined in the TypedDict.
        :NOTE: The input dict must still define all required keys of the TypedDict.

    :param dct: The dictionary to filter.
    :type dct: dict
    :param tp: The TypedDict type to use as the schema.
    :type tp: type[T]
    :return: The filtered dictionary.
    :rtype: T
    :raises ValidationError: If the input dictionary does not conform to the TypedDict schema.
    """
    return TypeAdapter(tp).validate_python(dct, extra="ignore")
