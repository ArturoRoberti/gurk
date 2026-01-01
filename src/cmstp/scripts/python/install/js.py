import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from packaging import version

from cmstp.core.logger import Logger
from cmstp.scripts.python.helpers._interface import get_config_args
from cmstp.scripts.python.helpers.common import add_alias
from cmstp.scripts.python.helpers.processing import (
    InstallCommands,
    get_clean_lines,
    install_packages_from_list,
)
from cmstp.utils.git_repos import (
    clone_git_files,
    gitref_dict2str,
    parse_git_ref,
)


def install_js_repositories(*args: List[str]) -> None:
    """
    Clone and install JS repositories from a list of git URLs.

    :param args: Configuration arguments
    :type args: List[str]
    """
    # Parse config args
    _, config_file, force, remaining_args = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping pulling of docker images, as no task config file is provided",
            warning=True,
        )
        return

    # Get JS repositories info
    repos = get_clean_lines(config_file)
    if not repos:
        Logger.step(
            "Skipping installation of JS repositories, as no repositories are specified",
        )
        return

    # (STEP) Installing Requirement(s)
    install_packages_from_list(InstallCommands.APT, ["npm", "nodejs", "git"])
    install_packages_from_list(InstallCommands.NPM, ["yarn", "pnpm"])

    # Directories for npm, yarn and pnpm packages
    yarn_pkg_dir = Path("/opt/yarn")
    pnpm_pkg_dir = Path("/opt/pnpm")
    npm_pkg_dir = Path("/opt/npm")

    # (STEP) Installing npm repositories
    for repo in repos:
        parsed = parse_git_ref(repo)
        pkg_name = Path(parsed["url"]).stem
        with TemporaryDirectory() as tmp:
            # Clone repo (shallow clone)
            parsed["depth"] = 1
            repo_path = clone_git_files(gitref_dict2str(parsed), tmp)
            if not repo_path:
                Logger.step(
                    f"Failed to clone repository {repo}, skipping.",
                    warning=True,
                )
                continue

            # Get package name from package.json if possible
            pkg_json = repo_path / "package.json"
            if not pkg_json.exists():
                Logger.step(
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
                    Logger.step(
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
                    cwd=repo_path,
                    shell=True,
                    check=True,
                )
            except subprocess.CalledProcessError:
                Logger.step(
                    f"Failed to install package {pkg_name}, skipping.",
                    warning=True,
                )
                continue

            # Move to /opt/npm (overwrite if exists) - TODO: Either generalize or (if only necessary for npm) change to npm only
            target = npm_pkg_dir / pkg_name
            if target.exists():
                if force:
                    subprocess.run(["sudo", "rm", "-rf", str(target)])
                else:
                    Logger.step(
                        f"Package {pkg_name} already exists at {target}, skipping.",
                        warning=True,
                    )
                    continue
            subprocess.run(
                ["sudo", "mv", str(repo_path), str(target)], check=True
            )

            # Add alias
            if "--create-aliases" in remaining_args:
                add_alias(
                    f"{pkg_name}='(cd {target} && {package_manager} start > /dev/null &)'"
                )

            Logger.step(f"Successfully installed {pkg_name} to {target}")
