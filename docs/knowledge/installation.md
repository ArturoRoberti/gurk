# Installation Guide
Installation of `gurk` is currently only supported on Ubuntu 22.04 and later versions. Support for other operating systems and Linux distributions might be added in the future. Please follow the instructions below to install `gurk` on your system.

# Prerequisites
## python3.12 (or higher) with pipx
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12
python3.12 -m pip install --user pipx
python3.12 -m pipx ensurepath
```

## git
```bash
sudo apt update && sudo apt install git
```

# Installation
After ensuring you have the prerequisites installed, you can install `gurk` using `pipx`:
```bash
python3.12 -m pipx install gurk
```
