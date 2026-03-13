#!/usr/bin/env bash
set -euo pipefail

# gurk installation script
# Supports Ubuntu 22.04+
# Usage: curl -sSL https://raw.githubusercontent.com/ArturoRoberti/gurk/main/install.bash | sudo bash [-s -- [OPTIONS]]
REPO_URL="https://raw.githubusercontent.com/ArturoRoberti/gurk/main"

# CLI options
DRY_RUN=false
FORCE=false

usage() {
	cat <<EOF
Usage: install.bash [OPTIONS]
       curl -sSL $REPO_URL/install.bash | sudo bash [-s -- [OPTIONS]]

Install gurk via pipx on Ubuntu 22.04+.

Options:
  -h, --help  Show this help message and exit
  --dry-run   Print what would be done without executing anything
  --force     Reinstall gurk even if already installed
EOF
	exit 0
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--dry-run) DRY_RUN=true ;;
		--force) FORCE=true ;;
		-h | --help) usage ;;
		*)
			echo "Unknown option: $1" >&2
			exit 1
			;;
	esac
	shift
done

# Colors
_color() {
	echo "\e[$1m"
}
NC=$(_color 0)
RED=$(_color 0\;31)
BLUE=$(_color 0\;34)
GREEN=$(_color 0\;32)
ORANGE=$(_color 0\;33)
BOLD_RED=$(_color 1\;31)
BOLD_BLUE=$(_color 1\;34)
BOLD_GREEN=$(_color 1\;32)
BOLD_ORANGE=$(_color 1\;33)

info() { echo -e "${BLUE}[gurk]${NC} $*"; }
success() { echo -e "${GREEN}[gurk]${NC} $*"; }
warn() { echo -e "${ORANGE}[gurk]${NC} $*"; }
error() { echo -e "${RED}[gurk]${NC} $*" >&2; }

UBUNTU_VERSION=$(lsb_release -rs 2>/dev/null | cut -d. -f1)
if [[ -z "$UBUNTU_VERSION" ]]; then
	error "Unsupported OS. This installer is designed for Ubuntu 22.04 or later."
	exit 1
elif [[ "$UBUNTU_VERSION" -lt 22 ]]; then
	error "Ubuntu 22.04 or later is required. Please upgrade your system."
	exit 1
fi

# Utilities
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
run_as_user() {
	sudo -u "$REAL_USER" env HOME="$REAL_HOME" "$@"
}

run_cmd() {
	if $DRY_RUN; then
		info "[dry-run] Would run: $*"
		return 0
	fi
	"$@" >/dev/null 2>&1
}

echo ""
echo -e "  ${BOLD_BLUE}gurk installer${NC}"
echo -e "  ${BLUE}Ubuntu $UBUNTU_VERSION detected${NC}"
echo ""

# Install dependencies
DEPS=(git curl)
MISSING=()
for dep in "${DEPS[@]}"; do
	if ! command -v "$dep" &>/dev/null; then
		MISSING+=("$dep")
	fi
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
	info "Installing dependencies: ${MISSING[*]}..."
	run_cmd apt-get update -qq
	run_cmd apt-get install -y -qq "${MISSING[@]}"
fi

# Read minimum Python version from pyproject.toml
MIN_PYTHON=$(curl -sSL "$REPO_URL/pyproject.toml" | sed -n 's/^requires-python.*>=\([0-9.]*\)".*/\1/p')
MIN_MAJOR=${MIN_PYTHON%%.*}
MIN_MINOR=${MIN_PYTHON##*.}

# Ensure python>=$MIN_PYTHON is installed
PYTHON=$(ls /usr/bin/python* 2>/dev/null | grep -E 'python3\.[0-9]+$' 2>/dev/null | sort -V | tail -n1)
if [[ -n "$PYTHON" ]]; then
	version=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
	major=${version%%.*}
	minor=${version##*.}
	if [[ "$major" -lt "$MIN_MAJOR" || ("$major" -eq "$MIN_MAJOR" && "$minor" -lt "$MIN_MINOR") ]]; then
		PYTHON=""
	fi
fi
if [[ -z "$PYTHON" ]]; then
	info "No Python >= $MIN_PYTHON found. Installing python$MIN_PYTHON..."
	run_cmd apt-get update -qq
	if ! run_cmd apt-get install -y -qq "python$MIN_PYTHON"; then
		warn "Not available via default repos, trying deadsnakes PPA..."
		run_cmd apt-get install -y -qq software-properties-common
		run_cmd add-apt-repository -y ppa:deadsnakes/ppa
		run_cmd apt-get update -qq
		run_cmd apt-get install -y -qq "python$MIN_PYTHON"
	fi
	run_cmd apt-get install -y -qq "python$MIN_PYTHON-venv"
	PYTHON="$(which "python$MIN_PYTHON")"
fi

# Ensure pipx is installed correctly
if [[ "$UBUNTU_VERSION" -ge 24 ]]; then
	if ! command -v pipx &>/dev/null; then
		info "Installing pipx via apt..."
		run_cmd apt-get update -qq
		run_cmd apt-get install -y -qq pipx
	fi
	run_cmd run_as_user pipx ensurepath
	PIPX=(pipx)
else
	info "Using python$MIN_PYTHON ($(run_as_user "$PYTHON" --version 2>&1))"
	if ! run_as_user "$PYTHON" -m pipx --version &>/dev/null 2>&1; then
		info "Installing pipx via pip..."
		run_cmd run_as_user "$PYTHON" -m pip install --user pipx
	fi
	run_cmd run_as_user "$PYTHON" -m pipx ensurepath
	PIPX=("$PYTHON" -m pipx)
fi

# Install gurk
PIPX_FORCE=()
if $FORCE; then
	PIPX_FORCE=(--force)
fi

info "Installing gurk..."
if [[ "$UBUNTU_VERSION" -ge 24 ]]; then
	run_cmd run_as_user "${PIPX[@]}" install "${PIPX_FORCE[@]}" --python "$PYTHON" gurk
else
	run_cmd run_as_user "${PIPX[@]}" install "${PIPX_FORCE[@]}" gurk
fi

echo ""
success "gurk installed successfully!"
info "Restart your shell or run: ${BOLD_BLUE}source $REAL_HOME/.bashrc${NC}"
