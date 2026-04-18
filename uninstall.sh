#!/usr/bin/env bash
set -euo pipefail

VIGIL_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/vigil"
AUTOSTART="$HOME/.config/autostart/vigil.desktop"
DESKTOP="${XDG_DATA_HOME:-$HOME/.local/share}/applications/vigil.desktop"
LAUNCHER="$HOME/.local/bin/vigil"

echo "Vigil uninstall — the following will be removed:"
echo ""

items=()
[[ -d "$VIGIL_DATA" ]] && items+=("  $VIGIL_DATA")
[[ -f "$AUTOSTART" ]]   && items+=("  $AUTOSTART")
[[ -f "$DESKTOP" ]]     && items+=("  $DESKTOP")
[[ -f "$LAUNCHER" ]]    && items+=("  $LAUNCHER")

if [[ ${#items[@]} -eq 0 ]]; then
    echo "  Nothing to remove — Vigil data not found."
    exit 0
fi

for item in "${items[@]}"; do echo "$item"; done
echo ""
read -rp "Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

[[ -d "$VIGIL_DATA" ]] && { rm -rf "$VIGIL_DATA"; echo "Removed: $VIGIL_DATA"; }
[[ -f "$AUTOSTART" ]]   && { rm -f  "$AUTOSTART";    echo "Removed: $AUTOSTART"; }
[[ -f "$DESKTOP" ]]     && { rm -f  "$DESKTOP";      echo "Removed: $DESKTOP"; }
[[ -f "$LAUNCHER" ]]    && { rm -f  "$LAUNCHER";     echo "Removed: $LAUNCHER"; }

echo ""
echo "Done. The Vigil source directory is NOT removed."
echo "  If you installed via curl, delete it manually:"
echo "    rm -rf \"\${XDG_DATA_HOME:-\$HOME/.local/share}/vigil-src\""
