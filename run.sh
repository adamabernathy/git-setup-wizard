#!/usr/bin/env bash
#
# run.sh — launcher for the Git Setup Wizard
#
# Checks for Python 3, installs the 'rich' package if missing,
# and runs the wizard. Intended for macOS.
#

set -euo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()  { printf "${BOLD}▸${RESET} %s\n" "$1"; }
ok()    { printf "${GREEN}✔${RESET} %s\n" "$1"; }
warn()  { printf "${YELLOW}⚠${RESET} %s\n" "$1"; }
fail()  { printf "${RED}✖ %s${RESET}\n" "$1"; exit 1; }

REPO_URL="https://raw.githubusercontent.com/adamabernathy/git-setup-wizard/main"

# ─── Locate or download the wizard script ────────────────────────────────────
# If run.sh lives next to the wizard (local clone), use that.
# If run via curl pipe, download the wizard to a temp directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || SCRIPT_DIR=""

if [[ -n "$SCRIPT_DIR" && -f "${SCRIPT_DIR}/git_setup_wizard.py" ]]; then
    WIZARD="${SCRIPT_DIR}/git_setup_wizard.py"
else
    TMPDIR_WIZARD="$(mktemp -d)"
    trap 'rm -rf "$TMPDIR_WIZARD"' EXIT
    info "Downloading git_setup_wizard.py..."
    if curl -fsSL "${REPO_URL}/git_setup_wizard.py" -o "${TMPDIR_WIZARD}/git_setup_wizard.py"; then
        ok "Downloaded wizard script"
    else
        fail "Could not download git_setup_wizard.py from GitHub"
    fi
    WIZARD="${TMPDIR_WIZARD}/git_setup_wizard.py"
fi

# ─── Check Python 3 ─────────────────────────────────────────────────────────
info "Checking for Python 3..."

if command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
    PY_VERSION="$("$PYTHON" --version 2>&1)"
    ok "Found ${PY_VERSION} at ${PYTHON}"
else
    fail "Python 3 is not installed. Install it with:  brew install python3"
fi

# Require Python 3.8+
PY_MINOR="$("$PYTHON" -c 'import sys; print(sys.version_info.minor)')"
if [[ "$PY_MINOR" -lt 8 ]]; then
    fail "Python 3.8+ is required (found 3.${PY_MINOR}). Run:  brew install python3"
fi

# ─── Check pip ───────────────────────────────────────────────────────────────
info "Checking for pip..."

if "$PYTHON" -m pip --version &>/dev/null; then
    ok "pip is available"
else
    warn "pip not found. Attempting to bootstrap it..."
    "$PYTHON" -m ensurepip --upgrade 2>/dev/null \
        || fail "Could not install pip. Run:  brew install python3"
    ok "pip bootstrapped"
fi

# ─── Install dependencies ───────────────────────────────────────────────────
info "Checking Python packages..."

install_package() {
    local pkg="$1"
    if "$PYTHON" -c "import ${pkg}" 2>/dev/null; then
        ok "${pkg} is installed"
    else
        info "Installing ${pkg}..."
        if "$PYTHON" -m pip install "$pkg" --quiet --break-system-packages 2>/dev/null; then
            ok "${pkg} installed"
        elif "$PYTHON" -m pip install "$pkg" --quiet 2>/dev/null; then
            ok "${pkg} installed"
        else
            fail "Could not install ${pkg}. Try manually:  pip3 install ${pkg}"
        fi
    fi
}

install_package "rich"

# ─── Run the wizard ──────────────────────────────────────────────────────────
printf "\n"
info "Launching Git Setup Wizard...\n"
exec "$PYTHON" "$WIZARD"
