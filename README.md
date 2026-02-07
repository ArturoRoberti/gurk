[![Contributing](https://img.shields.io/badge/contributing-guidelines-blue.svg)](https://github.com/ArturoRoberti/gurk/blob/main/.github/CONTRIBUTING.md)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/ArturoRoberti/gurk/blob/main/LICENSE)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-brown?logo=github)](https://github.com/ArturoRoberti/gurk)


![title image](./docs/assets/title_image.png)

🖥️ gurk 🥒 - The user-friendly package manager allowing customizable and repeatable computer setup

# Installation

## Ubuntu
Install dependencies:
```bash
sudo apt update
sudo apt install git pipx
```

Then, install and initialize `gurk`:
```bash
pipx install gurk
gurk init
```

## MacOS, Windows and other Linux distributions
Not supported yet.

# Usage
Using gurk you can run various plugins and tasks via
```bash
gurk run <plugin>[:<option> | /<task-subname>] [<task-args>]
```

where `<plugin>` is a plugin's git URL, the name of an installed plugin or a local path to a custom plugin. For example:
```bash
gurk run 'https://github.com/ArturoRoberti/example_gurk_plugin.git'
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
