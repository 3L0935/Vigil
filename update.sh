#!/usr/bin/env bash
# Vigil — update script
# Stops the running instance, pulls the latest code, syncs deps, and restarts.
set -euo pipefail

REPO_URL="https://github.com/3L0935/WritHer-Linux.git"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/vigil-src"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$(pwd)}")" 2>/dev/null && pwd || pwd)"
if [[ -f "$SCRIPT_DIR/main.py" && -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    INSTALL_DIR="$SCRIPT_DIR"
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
step()  { echo -e "${GREEN}==> ${BOLD}$1${NC}"; }
warn()  { echo -e "${YELLOW}WARN:${NC} $1"; }
die()   { echo -e "${RED}ERROR:${NC} $1" >&2; exit 1; }

[[ -d "$INSTALL_DIR" ]] || die "Vigil source directory not found: $INSTALL_DIR"

# If .git was removed by an older install, restore git tracking.
if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    step "Initialising git in $INSTALL_DIR..."
    git -C "$INSTALL_DIR" init -q
    git -C "$INSTALL_DIR" remote add origin "$REPO_URL"
elif ! git -C "$INSTALL_DIR" remote get-url origin &>/dev/null; then
    git -C "$INSTALL_DIR" remote add origin "$REPO_URL"
fi

# ── 1. Stop running instance ─────────────────────────────────────────────────
step "Checking for running Vigil instance..."
# Match any process whose cmdline contains the install dir (uv --directory ... or the venv python)
VIGIL_PIDS=$(pgrep -f "$INSTALL_DIR" 2>/dev/null | grep -v "^$$\$" || true)
WAS_RUNNING=false

if [[ -n "$VIGIL_PIDS" ]]; then
    WAS_RUNNING=true
    echo "  Stopping PID(s): $VIGIL_PIDS"
    kill -TERM $VIGIL_PIDS 2>/dev/null || true
    for i in {1..10}; do
        remaining=$(pgrep -f "$INSTALL_DIR" 2>/dev/null | grep -v "^$$\$" || true)
        [[ -z "$remaining" ]] && break
        sleep 0.5
    done
    remaining=$(pgrep -f "$INSTALL_DIR" 2>/dev/null | grep -v "^$$\$" || true)
    if [[ -n "$remaining" ]]; then
        warn "Graceful stop timed out, force-killing..."
        kill -KILL $remaining 2>/dev/null || true
        sleep 0.5
    fi
    step "Vigil stopped."
else
    echo "  Vigil is not running."
fi

# ── 2. Pull latest code ───────────────────────────────────────────────────────
step "Fetching latest changes..."
git -C "$INSTALL_DIR" fetch --depth=1 origin main
git -C "$INSTALL_DIR" reset --hard FETCH_HEAD

# ── 3. Refresh .desktop entries ───────────────────────────────────────────────
refresh_desktop() {
    local target="$1"
    [[ -f "$target" ]] || return 0
    cat > "$target" << DESKTOP
[Desktop Entry]
Type=Application
Name=Vigil
GenericName=Voice Assistant
Comment=Offline voice dictation and assistant
Exec=$HOME/.local/bin/vigil
Icon=$INSTALL_DIR/img/icon_vigil.png
Terminal=false
Categories=Utility;Audio;
Keywords=voice;dictation;assistant;speech;
StartupNotify=false
X-KDE-autostart-phase=2
X-GNOME-Autostart-Delay=5
DESKTOP
}

step "Refreshing .desktop entries..."
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
refresh_desktop "$DESKTOP_DIR/vigil.desktop"
refresh_desktop "$AUTOSTART_DIR/vigil.desktop"
# Prompt the icon cache to re-read (best-effort, no-op if missing)
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# ── 4. Sync Python dependencies ───────────────────────────────────────────────
step "Syncing Python dependencies..."
# Preserve TTS if it was installed (piper-tts is an optional dep — uv sync drops it without --extra)
SYNC_EXTRAS=""
if uv --directory "$INSTALL_DIR" run python -c "import piper" 2>/dev/null; then
    SYNC_EXTRAS="--extra tts-piper"
fi
uv --directory "$INSTALL_DIR" sync $SYNC_EXTRAS

# ── 5. Restart if it was running ─────────────────────────────────────────────
if [[ "$WAS_RUNNING" == true ]]; then
    sleep 0.5  # brief pause for PortAudio / PipeWire cleanup
    step "Restarting Vigil..."
    if command -v vigil >/dev/null 2>&1; then
        setsid vigil >/dev/null 2>&1 &
    else
        setsid uv --directory "$INSTALL_DIR" run python main.py >/dev/null 2>&1 &
    fi
    disown
    echo ""
    echo -e "${GREEN}${BOLD}Update complete — Vigil restarted.${NC}"
else
    echo ""
    echo -e "${GREEN}${BOLD}Update complete.${NC}"
    echo "  Run Vigil:  vigil"
fi
