#!/usr/bin/env bash
# simpleScreen installer for Linux and macOS
set -e

INSTALL_DIR="$HOME/.local/share/simpleScreen"
BIN_DIR="$HOME/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colours (safe fallback if tput is unavailable)
GREEN=$(tput setaf 2 2>/dev/null || true)
YELLOW=$(tput setaf 3 2>/dev/null || true)
RED=$(tput setaf 1 2>/dev/null || true)
RESET=$(tput sgr0 2>/dev/null || true)

ok()   { echo "  ${GREEN}[OK]${RESET} $*"; }
warn() { echo "  ${YELLOW}[!!]${RESET} $*"; }
err()  { echo "  ${RED}[ERROR]${RESET} $*"; exit 1; }
info() { echo "  $*"; }

echo ""
echo "====================================================="
echo "  simpleScreen Installer for Linux / macOS"
echo "====================================================="
echo ""

# ── 1. Check Python 3 ─────────────────────────────────────────────────────────
info "Checking for Python 3..."

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c "import sys; print(sys.version_info.major)")
        if [ "$version" -ge 3 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python 3 is required but not found.
  Install it via your package manager:
    Ubuntu/Debian : sudo apt-get install python3 python3-pip
    Fedora/RHEL   : sudo dnf install python3 python3-pip
    macOS         : brew install python"
fi

PY_VERSION=$("$PYTHON" --version)
ok "Found: $PY_VERSION"

# ── 2. Install Python dependencies ────────────────────────────────────────────
echo ""
info "Installing Python dependencies..."

if ! "$PYTHON" -m pip install --quiet --upgrade pip; then
    warn "Could not upgrade pip — continuing anyway."
fi

if ! "$PYTHON" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"; then
    # Try with --user flag
    warn "Retrying with --user flag..."
    "$PYTHON" -m pip install --quiet --user -r "$SCRIPT_DIR/requirements.txt" \
        || err "pip install failed. Check your internet connection."
fi

ok "Dependencies installed."

# ── 3. Copy files to install directory ────────────────────────────────────────
echo ""
info "Installing to: $INSTALL_DIR"

mkdir -p "$INSTALL_DIR/lib"
mkdir -p "$INSTALL_DIR/templates"
mkdir -p "$BIN_DIR"

cp "$SCRIPT_DIR/simpleScreen"      "$INSTALL_DIR/simpleScreen"
cp "$SCRIPT_DIR/requirements.txt"  "$INSTALL_DIR/requirements.txt"
cp "$SCRIPT_DIR/lib/"*.py          "$INSTALL_DIR/lib/"
cp "$SCRIPT_DIR/templates/"*       "$INSTALL_DIR/templates/"

chmod +x "$INSTALL_DIR/simpleScreen"
ok "Files copied."

# ── 4. Create launcher in PATH ─────────────────────────────────────────────────
echo ""
info "Creating launcher at $BIN_DIR/simpleScreen..."

# Write a small wrapper that calls the installed script via the correct Python
cat > "$BIN_DIR/simpleScreen" <<EOF
#!/usr/bin/env bash
exec "$PYTHON" "$INSTALL_DIR/simpleScreen" "\$@"
EOF
chmod +x "$BIN_DIR/simpleScreen"
ok "Launcher created."

# ── 5. Ensure ~/.local/bin is in PATH ─────────────────────────────────────────
if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    echo ""
    warn "$BIN_DIR is not in your PATH."
    info "Adding it now for future shell sessions..."

    SHELL_RC=""
    case "$SHELL" in
        */zsh)  SHELL_RC="$HOME/.zshrc" ;;
        */fish) SHELL_RC="$HOME/.config/fish/config.fish" ;;
        *)      SHELL_RC="$HOME/.bashrc" ;;
    esac

    if [ -n "$SHELL_RC" ]; then
        if [ "$SHELL" = "*/fish" ]; then
            echo "fish_add_path $BIN_DIR" >> "$SHELL_RC"
        else
            echo "" >> "$SHELL_RC"
            echo "# Added by simpleScreen installer" >> "$SHELL_RC"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        fi
        ok "Added to $SHELL_RC"
        # Apply to current session too
        export PATH="$BIN_DIR:$PATH"
    fi
fi

# ── 6. Check for screen ────────────────────────────────────────────────────────
echo ""
info "Checking for GNU screen..."
if command -v screen &>/dev/null; then
    ok "screen found: $(screen --version 2>&1 | head -1)"
else
    warn "GNU screen is not installed locally."
    info "For local sessions, install it:"
    info "  Ubuntu/Debian : sudo apt-get install screen"
    info "  Fedora/RHEL   : sudo dnf install screen"
    info "  macOS         : brew install screen"
    info "(Remote sessions will auto-install screen on the remote machine.)"
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo "====================================================="
ok "Installation complete!"
echo "====================================================="
echo ""
info "Start a new terminal session (or run: source ~/.bashrc)"
info "then type:"
echo ""
echo "    simpleScreen"
echo ""
info "to get started."
echo ""
