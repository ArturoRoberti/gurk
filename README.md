[![Contributing](https://img.shields.io/badge/contributing-guidelines-blue.svg)](https://github.com/ArturoRoberti/cmstp/blob/main/.github/CONTRIBUTING.md)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/ArturoRoberti/cmstp/blob/main/LICENSE)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-brown?logo=github)](https://github.com/ArturoRoberti/cmstp)


# cmstp - computer setup

Contains anything related to setting up a new computer (desktop) system.

# Disclaimer - Use at your own risk
This project is currently (12.2025) coded solely by me. As a junior developer, there is probably a lot that can be improved and although I have tested each task, there may be some unforeseen issues. Please use with caution and report any issues you find (see the [contributing](https://github.com/ArturoRoberti/cmstp/blob/main/README.md#contributing) section).

During this project's initial development, I recommend using it solely on fresh machines.

# Installation
## Prerequisites
### Ubuntu 24.04+
We recommend installing `pipx` via apt:
```bash
sudo apt update && sudo apt install pipx
```
### Older Ubuntu Versions
We recommend installing `pipx` via `pip`:
```bash
sudo apt update && sudo apt install python3 python3-pip && python3 -m pip install --user pipx
```
> **NOTE**: The installation of `pipx` via `pip` (as opposed to `apt`) is recommended on older versions, as the `apt` version is often outdated.

### MacOS
Not supported yet.

### Windows
Not supported yet.

## Main Installation
Then, install `cmstp` via `pipx`:
```bash
pipx install cmstp
```

# Usage
## Pre-Setup
We recommend setting up the following before running the main installation/configuration tasks:
- Configuring SSH keys for git (GitHub, GitLab, etc.) - some tasks may require cloning private repositories
- Disabling Secure Boot (e.g. for installing NVIDIA drivers)

You can use the provided helper to guide you through these steps:
```bash
cmstp pre-setup [-s] [-g]
```

The helper also provides further possible manual setup steps for configuring fresh systems.

> **NOTE**: You may also look up the general instructions for creating SSH keys [here](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key).

## Main Installations/Configurations
To use default installations/configurations, simply use (without any flags):
```
cmstp setup [-h] [-t TASKS [TASKS ...]] [-f CONFIG_FILE] [-d CONFIG_DIRECTORY] [-p] [-v]
```

To use custom config installation/configuration config files, use (flag shorthand: `-d`)
```bash
cmstp setup --config-directory </path/to/configs/ | git_url>
```
where `/path/to/configs/` is a directory containing multiple txt/json(c)/yaml/... configuration files (to be used by tasks as defined in this repo's `config/default.yaml` file) following this package's default `config/` directory. Each file in that directory should have the same name and structure as in the default. We **STRONGLY RECOMMEND** saving a personalized config directory as a git repository and providing the git URL instead of a local path. The repository will be cloned and used for the configurations. For more details and examples of configs, see [this README](https://github.com/ArturoRoberti/cmstp/blob/main/src/cmstp/config/README.md).

To easily specify multiple tasks to be run, use (flag shorthand: `-f`)
```bash
cmstp setup --config-file /path/to/config.yaml
```
where the config file should be a yaml file following the structure of the `config/enabled.yaml` file in this package. That config file contains detailed explanations. Should a relative path be provided, the file will first be searched for locally and then in the config directory.

To simply enable tasks with their default configurations, use (flag shorthand: `-t`)
```bash
cmstp setup --tasks TASK1 TASK2 ...
```
where `TASK1`, `TASK2`, ... are the task names as specified in the `config/enabled.yaml` file in this package. Task arguments may optionally be passed via colon separation, e.g. `--tasks task1:arg1:arg2 task2:arg1`, in which case they will override any existing arguments for those tasks. Note that the precedence for any fields passed to tasks is as follows: `CLI tasks` > `config file` > `default config`.

Further options are
- `--enable-all` to enable all tasks (takes precedence over config file)
- `--enable-dependencies` to automatically enable dependencies of enabled tasks (takes precedence over config file)
- `--disable-preparation` to disable updating/upgrading apt beforehand (not recommended)
- `-v, --verbose` to enable verbose logging

# Contributing
Please see [CONTRIBUTING.md](https://github.com/ArturoRoberti/cmstp/blob/main/.github/CONTRIBUTING.md) for contribution guidelines.

# License
This project is licensed under the MIT License - see the [LICENSE](https://github.com/ArturoRoberti/cmstp/blob/main/LICENSE) file for details.

# Possible Future Features
- Add uninstallations/deconfigurations and seprate configurations from installations. That could result in multiple entrypoints (instead of the current single `cmstp setup`):
    - `cmstp install` - for installations only
    - `cmstp configure` - for configurations only
    - `cmstp uninstall` - for uninstallations only
    - Possibly, a `cmstp deconfigure` for deconfigurations only
- Setup Browser Bookmarks
- Setup Autocompletions

# TODO
Please see [TODO.md](https://github.com/ArturoRoberti/cmstp/blob/main/TODO.md) for a list of planned improvements.
