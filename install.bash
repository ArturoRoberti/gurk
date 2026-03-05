#!/usr/bin/env bash
set -euo pipefail

# gurk installation script
# Supports Ubuntu 22.04+
# Usage: curl -sSL https://raw.githubusercontent.com/ArturoRoberti/gurk/main/install.bash | sudo bash

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
run_as_user() {
	sudo -u "$REAL_USER" env HOME="$REAL_HOME" "$@"
}

# ── git ──
if ! command -v git &>/dev/null; then
	echo "Installing git..."
	apt-get update -q
	apt-get install -y git
fi

# ── Python >= 3.12 ──
PYTHON=$(ls -1 /usr/bin/python3.* 2>/dev/null | sort -V | tail -n1)

# Verify the found version is >= 3.12
if [[ -n "$PYTHON" ]]; then
	version=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
	major=${version%%.*}
	minor=${version##*.}
	if [[ "$major" -lt 3 || ("$major" -eq 3 && "$minor" -lt 12) ]]; then
		PYTHON=""
	fi
fi

if [[ -z "$PYTHON" ]]; then
	echo "No Python >= 3.12 found. Installing python3.12 via deadsnakes PPA..."
	apt-get update -q
	apt-get install -y software-properties-common
	add-apt-repository -y ppa:deadsnakes/ppa
	apt-get update -q
	apt-get install -y python3.12
	PYTHON="python3.12"
fi

echo "Using $PYTHON ($(run_as_user "$PYTHON" --version))"

# ── pipx ──
if ! run_as_user "$PYTHON" -m pipx --version &>/dev/null 2>&1; then
	echo "Installing pipx..."
	run_as_user "$PYTHON" -m pip install --user pipx
fi
run_as_user "$PYTHON" -m pipx ensurepath

# ── gurk ──
echo "Installing gurk..."
run_as_user "$PYTHON" -m pipx install gurk

echo ""
echo "gurk installed successfully."
echo "Restart your shell or run: source $REAL_HOME/.bashrc"
