#!/usr/bin/env bash
# WritHer Linux — update script
# Stops the running instance, pulls the latest code, syncs deps, and restarts.
set -euo pipefail

INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/writher-src"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$(pwd)}")" 2>/dev/null && pwd || pwd)"
if [[ -f "$SCRIPT_DIR/main.py" && -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    INSTALL_DIR="$SCRIPT_DIR"
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
step()  { echo -e "${GREEN}==> ${BOLD}$1${NC}"; }
warn()  { echo -e "${YELLOW}WARN:${NC} $1"; }
die()   { echo -e "${RED}ERROR:${NC} $1" >&2; exit 1; }

[[ -d "$INSTALL_DIR" ]] || die "WritHer source directory not found: $INSTALL_DIR"
[[ -d "$INSTALL_DIR/.git" ]] || die "No git repository at $INSTALL_DIR — cannot update (curl install removes .git after setup)."

# ── 1. Stop running instance ─────────────────────────────────────────────────
step "Checking for running WritHer instance..."
# Match any process whose cmdline contains the install dir (uv --directory ... or the venv python)
WRITHER_PIDS=$(pgrep -f "$INSTALL_DIR" 2>/dev/null | grep -v "^$$\$" || true)
WAS_RUNNING=false

if [[ -n "$WRITHER_PIDS" ]]; then
    WAS_RUNNING=true
    echo "  Stopping PID(s): $WRITHER_PIDS"
    kill -TERM $WRITHER_PIDS 2>/dev/null || true
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
    step "WritHer stopped."
else
    echo "  WritHer is not running."
fi

# ── 2. Pull latest code ───────────────────────────────────────────────────────
step "Fetching latest changes..."
git -C "$INSTALL_DIR" fetch origin
git -C "$INSTALL_DIR" reset --hard origin/main

# ── 3. Sync Python dependencies ───────────────────────────────────────────────
step "Syncing Python dependencies..."
uv --directory "$INSTALL_DIR" sync

# ── 4. Restart if it was running ─────────────────────────────────────────────
if [[ "$WAS_RUNNING" == true ]]; then
    sleep 0.5  # brief pause for PortAudio / PipeWire cleanup
    step "Restarting WritHer..."
    if command -v writher >/dev/null 2>&1; then
        setsid writher >/dev/null 2>&1 &
    else
        setsid uv --directory "$INSTALL_DIR" run python main.py >/dev/null 2>&1 &
    fi
    disown
    echo ""
    echo -e "${GREEN}${BOLD}Update complete — WritHer restarted.${NC}"
else
    echo ""
    echo -e "${GREEN}${BOLD}Update complete.${NC}"
    echo "  Run WritHer:  writher"
fi
