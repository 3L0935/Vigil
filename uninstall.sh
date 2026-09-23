#!/usr/bin/env bash
set -euo pipefail

VIGIL_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/vigil"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/vigil.desktop"
DESKTOP="${XDG_DATA_HOME:-$HOME/.local/share}/applications/vigil.desktop"
LAUNCHER="${XDG_BIN_HOME:-$HOME/.local/bin}/vigil"
TRIGGER="${XDG_BIN_HOME:-$HOME/.local/bin}/vigil-trigger"
ICON="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps/vigil.png"

echo "Vigil uninstall — the following will be removed:"
echo ""

items=()
[[ -d "$VIGIL_DATA" ]] && items+=("  $VIGIL_DATA")
[[ -f "$AUTOSTART" ]]   && items+=("  $AUTOSTART")
[[ -f "$DESKTOP" ]]     && items+=("  $DESKTOP")
[[ -f "$LAUNCHER" ]]    && items+=("  $LAUNCHER")
[[ -f "$TRIGGER" ]]     && items+=("  $TRIGGER")
[[ -f "$ICON" ]]        && items+=("  $ICON")

if [[ ${#items[@]} -eq 0 ]]; then
    echo "  Nothing to remove — Vigil data not found."
    exit 0
fi

for item in "${items[@]}"; do echo "$item"; done
echo ""
read -rp "Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

# Clear compositor-level hotkey bindings (KGA entries, gsettings paths,
# managed blocks in hyprland/sway/niri configs) before the binary goes.
# Best-effort: never block the uninstall on this step.
if [[ -x "$LAUNCHER" ]]; then
    "$LAUNCHER" --uninstall-hotkeys 2>/dev/null || true
fi

[[ -d "$VIGIL_DATA" ]] && { rm -rf "$VIGIL_DATA"; echo "Removed: $VIGIL_DATA"; }
[[ -f "$AUTOSTART" ]]   && { rm -f  "$AUTOSTART";    echo "Removed: $AUTOSTART"; }
[[ -f "$DESKTOP" ]]     && { rm -f  "$DESKTOP";      echo "Removed: $DESKTOP"; }
[[ -f "$LAUNCHER" ]]    && { rm -f  "$LAUNCHER";     echo "Removed: $LAUNCHER"; }
[[ -f "$TRIGGER" ]]     && { rm -f  "$TRIGGER";      echo "Removed: $TRIGGER"; }
[[ -f "$ICON" ]]        && { rm -f  "$ICON";         echo "Removed: $ICON"; }
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$(dirname "$DESKTOP")" 2>/dev/null || true
command -v kbuildsycoca6 >/dev/null 2>&1 && kbuildsycoca6 --noincremental >/dev/null 2>&1 || true

echo ""
echo "Done. The Vigil source directory is NOT removed."
echo "  If you installed via curl, delete it manually:"
echo "    rm -rf \"\${XDG_DATA_HOME:-\$HOME/.local/share}/vigil-src\""
