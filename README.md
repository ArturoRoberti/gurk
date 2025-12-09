[![Contributing](https://img.shields.io/badge/contributing-guidelines-blue.svg)](.github/CONTRIBUTING.md)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-brown?logo=github)](https://github.com/ArturoRoberti/cmstp)


# cmstp - computer setup

Contains anything related to setting up a new computer (desktop) system.

# Disclaimer - Use at your own risk
This project is currently (12.2025) coded solely by me. As a junior developer, there is probably a lot that can be improved and although I have tested each task, there may be some unforeseen issues. Please use with caution and report any issues you find (see the [contributing](#contributing) section).

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
```
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
cmstp --config-directory </path/to/configs/ | git_url>
```
where `/path/to/configs/` is a directory containing multiple txt/json(c)/yaml/... configuration files (to be used by tasks as defined in this repo's `config/default.yaml` file) following this package's default `config/` directory. Each file in that directory should have the same name and structure as in the default. We **STRONGLY RECOMMEND** saving a personalized config directory as a git repository and providing the git URL instead of a local path. The repository will be cloned and used for the configurations. For more details and examples of configs, see [this README](src/cmstp/config/README.md).

To easily specify multiple tasks to be run, use (flag shorthand: `-f`)
```bash
cmstp --config-file /path/to/config.yaml
```
where the config file should be a yaml file following the structure of the `config/enabled.yaml` file in this package. That config file contains detailed explanations. Should a relative path be provided, the file will first be searched for locally and then in the config directory.

To simply enable tasks with their default configurations, use (flag shorthand: `-t`)
```bash
cmstp --tasks TASK1 TASK2 ...
```
where `TASK1`, `TASK2`, ... are the task names as specified in the `config/enabled.yaml` file in this package. If both `--config-directory` and `--tasks` are provided, the `--tasks` flag takes precedence for enabling tasks.

# Contributing
Please see [CONTRIBUTING.md](.github/CONTRIBUTING.md) for contribution guidelines.

# License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# Possible Future Features
- Add uninstallations/deconfigurations and seprate configurations from installations. That could result in multiple entrypoints (instead of the current single `cmstp setup`):
    - `cmstp install` - for installations only
    - `cmstp configure` - for configurations only
    - `cmstp uninstall` - for uninstallations only
    - Possibly, a `cmstp deconfigure` for deconfigurations only
- Setup Browser Bookmarks
- Setup Autocompletions

# TODO
Look for TODOs in code. Otherwise, look at:
## !!! Major !!!
- Update this README
- When using `-t task`, allow args to be passed, e.g. via `-t task:arg1:arg2`. Also, allow e.g. `enable_deps` to be passed
- Update and document pytests, and use them in CI (e.g. make sure there is no `✖ Failure` in output)
- Add descriptions to each function (inputs, outputs, what it does) both for python and bash
- Have a `--force` (and/or `--reinstall`) argument to override checks (i.e. run even if already installed/configured)
- See where `revert_sudo_permission` is necessary (isaac*, miniconda, .virtualenvs, configure-filestructure, ...) - include parent folders
## Minor
- Add mujoco stuff (mujoco, dmcontrol, sim applications)
- (If possible) Only run CI on new or edited tasks
- Add file with list of debian file links (then get and dpkg (or step apt?) them)
- Maybe, when cmstp is run for the very first time, propose to do pre-setup first (then create mock file in pkg or so to mark that cmstp was already run once)
    - Or just add big NOTE in README -> but that may not be seen by those installing via pipx
- Define and document behaviour of using none, one of, or both `--config-file` and `--config-directory`
    - How can a config file in a config dir repo be specified?
        - (Maybe) If it's an absolute path, look there. If it is relative, look locally and then in the repo
- Reduce the config files here to the most basic, non-invasive ones (just to have some example)
- Test cyclic `supercedes` fields
- Update logging to file (i.e. `CMSTP START ...`) to only have a single CMSTP section, and fill stuff in there
- Remove uninstallations from "enable_all" etc. Or better, have a "counterpart" field or similar and if both install/uninstall are enabled, disable uninstall (say this in debug, not info/warning message)
- It seems that something may suspend all tasks running (if many are running)
    - Maybe this is caused by one task failing?
    - Can be restarted sing `fg %<id>` (bash; manually) (see id from output: `[<id>]+ Stopped`), but ofc that should not be necessary in the long term
- Maybe add a `requires-restart` flag or so to each task and make final message depend on that
- If a dependency task fails, downstream tasks should not be run
- If verbose is set, save the modified scripts in log dir
- Make dev instructions (e.g. to add a task, edit <...>; to add a field to tasks, edit <...>; to add a test, edit <...>; etc.)
- Remove `sudo: mon_handle_sigchld: waitpid: No child processes` outputs
