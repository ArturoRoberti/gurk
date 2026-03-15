# Installation Guide
Installation of `gurk` is currently only supported on Ubuntu 22.04 and later versions. Support for other operating systems and Linux distributions might be added in the future. We highly recommend the installation script provided in this repo's README - otherwise, please follow the instructions below to install `gurk` on your system.

# Prerequisites
## Ubuntu22.04
You need `python3.12` (or higher) installed:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv
```

Then, you can install `pipx`:
```bash
python3.12 -m pip install --user pipx
python3.12 -m pipx ensurepath
```

## Ubuntu24.04+
`python3.12` (or higher) should be installed by default (check: `python3 --version`). If not, follow the [Ubuntu22.04 instructions](#ubuntu2204) in this entire installation guide. If so, install `pipx` via apt:
```bash
sudo apt update
sudo apt install pipx
pipx ensurepath
```

## OS-agnostic
You need git installed for plugin management to work:
```bash
sudo apt update && sudo apt install git
```

# Installation
After ensuring you have the prerequisites installed, you can install `gurk` using `pipx`:
```bash
[python3.12 -m] pipx install gurk
```

You can later keep gurk up-to-date via:
```bash
[python3.12 -m] pipx upgrade gurk
```

# Uninstallation
To fully remove `gurk` from your system, run the following two commands:

```bash
gurk clean --purge    # removes all gurk data, config, cache, and log directories
pipx uninstall gurk   # removes the gurk package itself
```

Running `gurk clean` without `--purge` only removes ephemeral directories (cache and logs) and is safe to run at any time.
