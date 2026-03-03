#!/usr/bin/env python3

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

import sys

import tomli_w

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def format_file(file: str) -> None:
    # Load test.toml
    with open(file, "rb") as f:
        data = tomllib.load(f)

    # Write it back
    with open(file, "wb") as f:
        tomli_w.dump(data, f, indent=2)


if __name__ == "__main__":
    paths = sys.argv[1:]
    for p in paths:
        format_file(p)
