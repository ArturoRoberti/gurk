[![License](https://img.shields.io/badge/License-Apache%202.0-yellow?logo=apache&logoColor=white)]()
[![GitHub](https://img.shields.io/badge/GitHub-grey?logo=github)](https://github.com/ArturoRoberti/gurk)
[![PyPI](https://img.shields.io/badge/PyPI-3775A9?logo=pypi&logoColor=white)](https://pypi.org/project/gurk)
[![Contributing](https://img.shields.io/badge/Contributing%20Guidelines-grey?logo=contributorcovenant&logoColor=white)](https://github.com/ArturoRoberti/gurk/tree/main/.github/CONTRIBUTING.md)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)

![title image](./docs/assets/title_image.png)

🖥️ gurk 🥒 - The user-friendly package manager allowing customizable and repeatable computer setup

# Installation (Ubuntu 22.04+ only)
Please use the provided installation script (recommended):
```bash
sudo apt update && sudo apt install curl
curl -fsSL https://raw.githubusercontent.com/ArturoRoberti/gurk/main/install.sh | sudo bash
```

or follow the instructions in the [Installation Guide](https://github.com/ArturoRoberti/gurk/tree/main/docs/knowledge/installation.md).

# Usage
Using gurk you can run various plugins and tasks via
```bash
gurk run <plugin>[:<option> | /<task-subname>] [<task-args>]
```

where `<plugin>` is a plugin's git URL, the name of an installed plugin or a local path to a custom plugin. Please have a brief look at the [documentation](https://github.com/ArturoRoberti/gurk/tree/main/docs/knowledge/) for more information.

## Examples
Install docker via the docker plugin:
```bash
gurk run docker/install-docker
```

Install conda via the conda plugin:
```bash
gurk run conda/install-conda
```

See available arguments for the conda plugin:
```bash
gurk run conda --help  # OR 'gurk run conda/install-conda --help' for the specific task
```

Run the example plugin, which installs and configures multiple programs commonly used:
```bash
gurk run 'https://github.com/ArturoRoberti/gurk_example_plugin.git:setup'
```

# Contributing
Please see [CONTRIBUTING.md](https://github.com/ArturoRoberti/gurk/tree/main/.github/CONTRIBUTING.md) for contribution guidelines.

# License
This project is licensed under the Apache 2.0 License - see the [LICENSE](https://github.com/ArturoRoberti/gurk/tree/main/LICENSE) file for details.

# TODO
Please see [TODO.md](https://github.com/ArturoRoberti/gurk/tree/main/TODO.md) for a list of planned improvements and features.
