#!/usr/bin/env bash
# Vigil — distro-agnostic installer
set -euo pipefail

REPO_URL="https://github.com/3L0935/WritHer-Linux.git"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/vigil-src"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'

step()  { echo -e "${GREEN}==> ${BOLD}$1${NC}"; }
warn()  { echo -e "${YELLOW}WARN:${NC} $1"; }
die()   { echo -e "${RED}ERROR:${NC} $1" >&2; exit 1; }


# ── Detect source directory ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$(pwd)}")" 2>/dev/null && pwd || pwd)"
_IN_REPO=false
if [[ -f "$SCRIPT_DIR/main.py" && -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    INSTALL_DIR="$SCRIPT_DIR"
    _IN_REPO=true
    step "Using existing source: $INSTALL_DIR"
fi

# ── Install uv if missing ────────────────────────────────────────────────────
if ! command -v uv >/dev/null 2>&1; then
    step "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
command -v uv >/dev/null 2>&1 || die "uv not found after install. Re-open your terminal and re-run."

# ── Download source (curl/remote install only) ───────────────────────────────
if [[ "$_IN_REPO" == false ]]; then
    command -v git >/dev/null 2>&1 || die "git is required. Install it with your package manager."
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        step "Updating existing installation..."
        git -C "$INSTALL_DIR" fetch origin
        git -C "$INSTALL_DIR" reset --hard origin/main
    else
        step "Downloading Vigil..."
        rm -rf "$INSTALL_DIR"
        git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
    fi
fi

# ── Install Python dependencies ──────────────────────────────────────────────
step "Installing Python dependencies (this may take a minute)..."
uv --directory "$INSTALL_DIR" sync

# ── Create launcher script ───────────────────────────────────────────────────
step "Creating launcher: $BIN_DIR/vigil"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/vigil" << LAUNCHER
#!/usr/bin/env bash
exec uv --directory "$INSTALL_DIR" run python main.py "\$@"
LAUNCHER
chmod +x "$BIN_DIR/vigil"

# ── Create .desktop entry ────────────────────────────────────────────────────
step "Creating desktop entry..."
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/vigil.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=Vigil
GenericName=Voice Assistant
Comment=Offline voice dictation and assistant
Exec=$BIN_DIR/vigil
Icon=$INSTALL_DIR/img/icon_vigil.png
Terminal=false
Categories=Utility;Audio;
Keywords=voice;dictation;assistant;speech;
StartupNotify=false
DESKTOP

# ── Optional autostart ───────────────────────────────────────────────────────
echo ""
read -rp "$(echo -e "${BOLD}Add Vigil to autostart?${NC} [y/N] ")" autostart </dev/tty
if [[ "${autostart:-n}" =~ ^[Yy]$ ]]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$DESKTOP_DIR/vigil.desktop" "$AUTOSTART_DIR/vigil.desktop"
    step "Autostart enabled."
fi

# ── PATH warning ─────────────────────────────────────────────────────────────
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR is not in your PATH."
    echo "  Add this line to your ~/.bashrc, ~/.zshrc, or ~/.config/fish/config.fish:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

# ── First-run setup ──────────────────────────────────────────────────────────
echo ""
step "Running first-time setup wizard..."
echo "(This will download llama-server, a model, and optionally Piper TTS voices)"
echo ""
uv --directory "$INSTALL_DIR" run python first_run.py


# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}Installation complete!${NC}"
echo ""
echo "  Run Vigil:  vigil"
echo "  Or launch from your application menu."
echo ""
echo "  To uninstall: curl -fsSL https://raw.githubusercontent.com/3L0935/WritHer-Linux/main/uninstall.sh | bash"
