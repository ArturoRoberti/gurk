[![Contributing](https://img.shields.io/badge/contributing-guidelines-blue.svg)](https://github.com/ArturoRoberti/gurk/blob/main/.github/CONTRIBUTING.md)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/ArturoRoberti/gurk/blob/main/LICENSE)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-brown?logo=github)](https://github.com/ArturoRoberti/gurk)


![title image](./docs/assets/title_image.png)

🖥️ gurk 🥒 - The user-friendly package manager allowing customizable and repeatable computer setup

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
> [!NOTE]
> The installation of `pipx` via `pip` (as opposed to `apt`) is recommended on older versions, as the `apt` version is often outdated.

### MacOS
Not supported yet.

### Windows
Not supported yet.

## Main Installation
Then, install `gurk` via `pipx`:
```bash
pipx install gurk && gurk init
```

# Usage
Using gurk you can run various plugins via
```bash
gurk run --plugin <plugin> [args...]
```

where `<plugin>` is a plugin's git URL or the name of a locally installed plugin to run. For example:
```bash
gurk run --plugin 'git@github.com:ArturoRoberti/example_gurk_plugin.git'
```
> [!WARNING]
> Make sure to wrap git URLs in quotes to avoid shell interpretation issues with special characters (e.g. `&`)

Please have a brief look at the [documentation](https://github.com/ArturoRoberti/gurk/blob/main/docs/knowledge/) for more information.

# Contributing
Please see [CONTRIBUTING.md](https://github.com/ArturoRoberti/gurk/blob/main/.github/CONTRIBUTING.md) for contribution guidelines.

# License
This project is licensed under the MIT License - see the [LICENSE](https://github.com/ArturoRoberti/gurk/blob/main/LICENSE) file for details.

# TODO
Please see [TODO.md](https://github.com/ArturoRoberti/gurk/blob/main/TODO.md) for a list of planned improvements and features.
