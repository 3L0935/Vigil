#!/usr/bin/env bash
set -e

WRITHER_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/writher"
AUTOSTART="$HOME/.config/autostart/writher.desktop"
DESKTOP="$HOME/.local/share/applications/writher.desktop"

echo "WritHer uninstall — the following will be removed:"
echo ""

items=()
[[ -d "$WRITHER_DATA" ]] && items+=("  $WRITHER_DATA")
[[ -f "$AUTOSTART" ]]   && items+=("  $AUTOSTART")
[[ -f "$DESKTOP" ]]     && items+=("  $DESKTOP")

if [[ ${#items[@]} -eq 0 ]]; then
    echo "  Nothing to remove — WritHer data not found."
    exit 0
fi

for item in "${items[@]}"; do echo "$item"; done
echo ""
read -rp "Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

[[ -d "$WRITHER_DATA" ]] && { rm -rf "$WRITHER_DATA"; echo "Removed: $WRITHER_DATA"; }
[[ -f "$AUTOSTART" ]]   && { rm -f  "$AUTOSTART";    echo "Removed: $AUTOSTART"; }
[[ -f "$DESKTOP" ]]     && { rm -f  "$DESKTOP";      echo "Removed: $DESKTOP"; }

echo ""
echo "Done. The WritHer source directory is NOT removed — delete it manually if needed."
