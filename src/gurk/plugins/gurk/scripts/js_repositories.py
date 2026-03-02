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

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from packaging import version

from gurk import (
    BuiltinInstallCommands,
    add_alias,
    extract_url,
    get_clean_lines,
    git_clone,
    install_packages_from_list,
    log_step,
    parse_task_args,
)


def install_js_repositories(*args: list[str]) -> None:
    """
    Clone and install JS repositories from a list of git URLs.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # Get JS repositories info
    repos = get_clean_lines(task_args.config_file)
    if not repos:
        log_step(
            "Skipping installation of JS repositories, as no repositories are specified",
        )
        return

    # (STEP) Installing Requirement(s)
    install_packages_from_list(
        BuiltinInstallCommands.APT, ["npm", "nodejs", "git"]
    )
    install_packages_from_list(BuiltinInstallCommands.NPM, ["yarn", "pnpm"])

    # Directories for npm, yarn and pnpm packages
    yarn_pkg_dir = Path("/opt/yarn")
    pnpm_pkg_dir = Path("/opt/pnpm")
    npm_pkg_dir = Path("/opt/npm")

    # (STEP) Installing npm repositories
    for repo in repos:
        pkg_name = Path(extract_url(repo)).stem
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            # Clone repo
            try:
                git_clone(repo, tmp)
            except subprocess.CalledProcessError:
                log_step(
                    f"Failed to clone repository {repo}, skipping.",
                    warning=True,
                )
                continue

            # Get package name from package.json if possible
            pkg_json = tmp / "package.json"
            if not pkg_json.exists():
                log_step(
                    f"No package.json found in {repo}, skipping.", warning=True
                )
                continue
            with pkg_json.open() as f:
                pkg_json_data = json.load(f)

            # Check Node.js version if specified
            engines = pkg_json_data.get("engines", {})
            node_range = engines.get("node", None)
            if node_range is not None:
                # Get Node.js version
                result = subprocess.run(
                    ["node", "--version"], capture_output=True, text=True
                )
                node_version_str = result.stdout.strip().lstrip("v")
                node_version = version.parse(node_version_str)

                # Parse the version range - Replace 'x' with 0 in min version, 999 in max version
                min_str, max_str = [s.strip() for s in node_range.split("-")]
                min_version_str = ".".join(
                    "0" if part.lower() == "x" else part
                    for part in min_str.split(".")
                )
                max_version_str = ".".join(
                    "999" if part.lower() == "x" else part
                    for part in max_str.split(".")
                )
                min_version = version.parse(min_version_str)
                max_version = version.parse(max_version_str)

                if not (min_version <= node_version <= max_version):
                    log_step(
                        f"Skipping installation of {pkg_name}, as Node.js version {node_version} does not satisfy required range {node_range}.",
                        warning=True,
                    )
                    continue

            # Determine package manager
            package_manager_entry = pkg_json_data.get("packageManager", "npm")
            if package_manager_entry.startswith("yarn"):
                package_manager = "yarn install"
                pkg_dir = yarn_pkg_dir
            elif package_manager_entry.startswith("pnpm"):
                package_manager = "pnpm install"
                pkg_dir = pnpm_pkg_dir
            else:
                package_manager = "npm install"
                pkg_dir = npm_pkg_dir
            if not pkg_dir.exists():
                subprocess.run(["sudo", "mkdir", "-p", str(pkg_dir)])
            # Install package
            try:
                subprocess.run(
                    f"{package_manager} install",
                    cwd=tmp,
                    shell=True,
                    check=True,
                )
            except subprocess.CalledProcessError:
                log_step(
                    f"Failed to install package {pkg_name}, skipping.",
                    warning=True,
                )
                continue

            # Move to /opt/npm (overwrite if exists) - TODO: Either generalize or (if only necessary for npm) change to npm only
            target = npm_pkg_dir / pkg_name
            if target.exists():
                if task_args.force:
                    subprocess.run(["sudo", "rm", "-rf", str(target)])
                else:
                    log_step(
                        f"Package {pkg_name} already exists at {target}, skipping.",
                        warning=True,
                    )
                    continue
            subprocess.run(["sudo", "mv", str(tmp), str(target)], check=True)

            # Add alias
            if task_args.gurk_js_create_aliases:
                add_alias(
                    f"{pkg_name}='(cd {target} && {package_manager} start > /dev/null &)'"
                )

            log_step(f"Successfully installed {pkg_name} to {target}")
