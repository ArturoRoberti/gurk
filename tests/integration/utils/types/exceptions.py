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


class _PytestException(Exception):
    """Base class for custom exceptions in pytests."""

    def __init__(self, message: str):
        prefix = f"[{self.__class__.__name__}] "
        super().__init__(prefix + message)


class PytestInputException(_PytestException):
    """Custom exception type for invalid input in pytests."""

    def __init__(self, message: str):
        prefix = "Invalid input: "
        super().__init__(prefix + message)


class PytestUnexpectedException(_PytestException):
    """Exception raised when an unexpected error occurs during testing."""

    def __init__(self, message: str):
        prefix = "Unexpected error: "
        super().__init__(prefix + message)
