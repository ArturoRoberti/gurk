[![License](https://img.shields.io/badge/License-Apache%202.0-yellow?logo=apache&logoColor=white)]()
[![GitHub](https://img.shields.io/badge/GitHub-grey?logo=github)](https://github.com/ArturoRoberti/gurk)
[![PyPI](https://img.shields.io/badge/PyPI-3775A9?logo=pypi&logoColor=white)](https://pypi.org/project/gurk)
[![Contributing](https://img.shields.io/badge/Contributing%20Guidelines-grey?logo=contributorcovenant&logoColor=white)](https://github.com/ArturoRoberti/gurk/blob/main/.github/CONTRIBUTING.md)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)

![title image](./docs/assets/title_image.png)

🖥️ gurk 🥒 - The user-friendly package manager allowing customizable and repeatable computer setup

# Installation

## Ubuntu (22.04+)
Ensure you have `pipx` installed via `python3.12` (or higher) and `git`:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 git
python3.12 -m pip install --user pipx
python3.12 -m pipx ensurepath
```

Then, install `gurk` via:
```bash
pipx install gurk
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
gurk run 'https://github.com/ArturoRoberti/gurk_example_plugin.git'
```
> [!WARNING]
> Make sure to wrap git URLs in quotes to avoid shell interpretation issues with special characters (e.g. `&`)

Please have a brief look at the [documentation](https://github.com/ArturoRoberti/gurk/blob/main/docs/knowledge/) for more information.

# Contributing
Please see [CONTRIBUTING.md](https://github.com/ArturoRoberti/gurk/blob/main/.github/CONTRIBUTING.md) for contribution guidelines.

# License
This project is licensed under the Apache 2.0 License - see the [LICENSE](https://github.com/ArturoRoberti/gurk/blob/main/LICENSE) file for details.

# TODO
Please see [TODO.md](https://github.com/ArturoRoberti/gurk/blob/main/TODO.md) for a list of planned improvements and features.
