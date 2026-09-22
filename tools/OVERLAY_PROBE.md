# Qt Quick overlay probe on KDE Plasma Wayland

Date: 2026-09-22. Host: KDE Plasma Wayland, three displays (`DP-2`, `DP-3`,
`HDMI-A-1`), AMD graphics. The probe is `tools/overlay_probe.py`; it creates a
252 × 50 `QQuickWindow` for every screen and each of the nine anchors. It sets
`Tool`, `FramelessWindowHint`, `WindowStaysOnTopHint`, and
`WindowDoesNotAcceptFocus`, then reads the position, screen, focus state, and
flags after 220 ms.

Commands:

```bash
QT_QPA_PLATFORM=wayland .venv/bin/python tools/overlay_probe.py > /tmp/vigil-wayland-overlay.jsonl
QT_QPA_PLATFORM=xcb .venv/bin/python tools/overlay_probe.py > /tmp/vigil-xcb-overlay.jsonl
QT_QPA_PLATFORM=xcb QT_SCALE_FACTOR=1.5 .venv/bin/python tools/overlay_probe.py > /tmp/vigil-xcb-scale15-overlay.jsonl
```

| Qt platform | Cases | Requested screen reported back | Active overlay | Requested position reported back |
|---|---:|---:|---:|---:|
| `wayland` | 27 | 0/27 | 27/27 | 27/27 |
| `xcb` | 27 | 27/27 | 0/27 | 18/27 |
| `xcb`, 1.5× scale | 27 | 27/27 | 0/27 | 18/27 |

The native Wayland position equality is **not evidence of correct desktop
placement**: Qt reported a different `QScreen` for every case and reported the
overlay active despite the focus hint. Qt documents that XDG Shell does not
support client-controlled top-level window positioning, so coordinates read
back from Qt cannot validate actual placement there. See the [Qt window
positioning documentation](https://doc.qt.io/qt-6/qml-qtquick-window.html) and
[Wayland notes for application windows](https://doc.qt.io/qt-6/application-windows.html).

With `xcb`, all screens matched and no overlay became active. KWin clamped the
nine bottom anchors upward by 32–34 logical pixels at 1× and 13–15 logical
pixels at 1.5×. The script requested positions from `availableGeometry()`,
which appears to extend into an area KWin reserves near the bottom edge; the
production placement adapter must account for the observed work area. The probe did not prove
always-on-top stacking against another application, nor did it validate the
existing active-window screen tracker or runtime focus in a real recording.

## Cutover decision

The candidate is the `xcb` Qt platform for the full Vigil UI process on this
KDE Wayland host while overlay positioning is required. Qt's platform choice is
process-wide; a separate `xcb` overlay process would violate the single UI
loop decision in the Fold spec. Keep the platform selection in a small Linux
launcher adapter and leave native Wayland as a measured, unsupported overlay
path until a compositor-specific positioning adapter is available. The
production switch remains gated on stacking, the active-screen preference,
focus against a non-Vigil target, and the actual recording/answer views on the
same platform.
