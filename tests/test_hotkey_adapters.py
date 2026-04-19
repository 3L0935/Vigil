"""File-based adapters (Hyprland, Sway, niri) + manual fallback."""

from unittest.mock import patch

import pytest

import hotkey.hyprland as hypr
import hotkey.manual as manual
import hotkey.niri as niri
import hotkey.sway as sway


# ── combo conversion ────────────────────────────────────────────────────

def test_hyprland_combo_ctrl_alt_w():
    mods, key = hypr._to_hyprland_combo("Ctrl+Alt+W")
    assert mods == "CTRL ALT"
    assert key == "W"


def test_hyprland_combo_super():
    mods, key = hypr._to_hyprland_combo("Super+Space")
    assert mods == "SUPER"
    assert key == "Space"


def test_sway_combo_mapping():
    # Sway prefers Mod1 over "Alt" and lowercase letters.
    assert sway._to_sway_combo("Ctrl+Alt+W") == "Ctrl+Mod1+w"
    assert sway._to_sway_combo("Super+Return") == "Mod4+Return"


def test_niri_combo_title_case():
    assert niri._to_niri_combo("Ctrl+Alt+W") == "Ctrl+Alt+W"
    assert niri._to_niri_combo("Super+Space") == "Super+Space"


# ── Hyprland round-trip via ConfigBlockAdapter ──────────────────────────

def test_hyprland_register_writes_block(tmp_path, monkeypatch):
    cfg = tmp_path / "hyprland.conf"
    cfg.write_text("# existing hypr config\n")

    ad = hypr.HyprlandAdapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg)
    monkeypatch.setattr(ad, "_reload", lambda: None)

    assert ad.register("dictate", "Ctrl+Alt+W",
                       command=["vigil-trigger", "dictate"]) is True

    body = cfg.read_text()
    assert "# >>> vigil managed" in body
    assert "bind = CTRL ALT, W, exec, vigil-trigger dictate" in body
    assert "# id=dictate" in body
    assert ad.list_registered() == ["dictate"]


def test_hyprland_register_two_actions_same_block(tmp_path, monkeypatch):
    cfg = tmp_path / "hyprland.conf"
    cfg.write_text("")

    ad = hypr.HyprlandAdapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg)
    monkeypatch.setattr(ad, "_reload", lambda: None)

    ad.register("dictate", "Ctrl+Alt+W")
    ad.register("assistant", "Ctrl+Alt+R")

    body = cfg.read_text()
    # A single managed block, containing both lines.
    assert body.count("# >>> vigil managed") == 1
    assert body.count("# <<< vigil managed") == 1
    assert "id=dictate" in body and "id=assistant" in body
    assert set(ad.list_registered()) == {"dictate", "assistant"}


def test_hyprland_unregister_last_removes_block(tmp_path, monkeypatch):
    cfg = tmp_path / "hyprland.conf"
    cfg.write_text("# user stuff\n")

    ad = hypr.HyprlandAdapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg)
    monkeypatch.setattr(ad, "_reload", lambda: None)

    ad.register("dictate", "Ctrl+Alt+W")
    ad.unregister("dictate")

    body = cfg.read_text()
    assert "vigil managed" not in body
    assert "# user stuff" in body


# ── Sway round-trip ─────────────────────────────────────────────────────

def test_sway_format_line():
    cfg = sway.SwayAdapter()
    line = cfg._format_binding("dictate", "Ctrl+Alt+W",
                               ["vigil-trigger", "dictate"])
    assert line == "bindsym Ctrl+Mod1+w exec vigil-trigger dictate"


def test_sway_register_idempotent(tmp_path, monkeypatch):
    cfg_path = tmp_path / "sway" / "config"
    cfg_path.parent.mkdir()
    cfg_path.write_text("")

    ad = sway.SwayAdapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg_path)
    monkeypatch.setattr(ad, "_reload", lambda: None)

    ad.register("dictate", "Ctrl+Alt+W")
    ad.register("dictate", "Ctrl+Alt+W")  # second call: same result
    body = cfg_path.read_text()
    assert body.count("bindsym Ctrl+Mod1+w") == 1


# ── niri — KDL, nested inside binds { } ─────────────────────────────────

def test_niri_register_inside_binds_block(tmp_path, monkeypatch):
    cfg = tmp_path / "config.kdl"
    cfg.write_text(
        "// existing niri config\n\n"
        "binds {\n"
        '    Mod+Return { spawn "alacritty"; }\n'
        "}\n"
    )

    ad = niri.NiriAdapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg)

    ok = ad.register("dictate", "Ctrl+Alt+W",
                     command=["vigil-trigger", "dictate"])
    assert ok is True

    body = cfg.read_text()
    # Our fence is KDL-commented (//), inside the binds block.
    assert "// >>> vigil managed" in body
    assert "// <<< vigil managed" in body
    # Original binding survives.
    assert 'Mod+Return { spawn "alacritty"; }' in body
    # Our binding is present.
    assert 'Ctrl+Alt+W { spawn "vigil-trigger" "dictate"; }' in body
    # Fence lives inside the `binds { ... }` block — use production
    # brace-depth helper to find the real close brace.
    span = niri._find_binds_block(body)
    assert span is not None
    open_end, close_start = span
    fence_pos = body.index("// >>> vigil managed")
    assert open_end < fence_pos < close_start


def test_niri_no_existing_binds_block_creates_one(tmp_path, monkeypatch):
    cfg = tmp_path / "config.kdl"
    cfg.write_text("// just a comment\n")

    ad = niri.NiriAdapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg)

    ad.register("dictate", "Ctrl+Alt+W")
    body = cfg.read_text()
    assert "binds {" in body
    assert "// >>> vigil managed" in body


def test_niri_unregister_empties_block(tmp_path, monkeypatch):
    cfg = tmp_path / "config.kdl"
    cfg.write_text("binds {\n}\n")

    ad = niri.NiriAdapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg)

    ad.register("dictate", "Ctrl+Alt+W")
    assert ad.list_registered() == ["dictate"]

    ad.unregister("dictate")
    assert ad.list_registered() == []
    body = cfg.read_text()
    # Block is gone; binds { } remains (possibly empty).
    assert "vigil managed" not in body


# ── Manual fallback ─────────────────────────────────────────────────────

def test_manual_register_returns_false_and_logs():
    ad = manual.ManualAdapter()
    with patch("hotkey.manual.log.warning") as warn:
        ok = ad.register("dictate", "Ctrl+Alt+W",
                         command=["vigil-trigger", "dictate"])
    assert ok is False
    # At least one warning referencing the keybind and command.
    joined = " ".join(str(c) for c in warn.call_args_list)
    assert "Ctrl+Alt+W" in joined
    assert "vigil-trigger dictate" in joined


def test_manual_unregister_noop():
    ad = manual.ManualAdapter()
    assert ad.unregister("dictate") is True


# ── ConfigBlockAdapter helpers shared by hypr/sway ──────────────────────

@pytest.mark.parametrize("Adapter", [hypr.HyprlandAdapter, sway.SwayAdapter])
def test_file_based_adapter_register_returns_true_when_reload_succeeds(
        Adapter, tmp_path, monkeypatch):
    cfg = tmp_path / "conf"
    cfg.write_text("")

    ad = Adapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg)
    monkeypatch.setattr(ad, "_reload", lambda: None)

    assert ad.register("dictate", "Ctrl+Alt+W") is True


@pytest.mark.parametrize("Adapter", [hypr.HyprlandAdapter, sway.SwayAdapter])
def test_file_based_adapter_returns_false_when_reload_raises(
        Adapter, tmp_path, monkeypatch):
    cfg = tmp_path / "conf"
    cfg.write_text("")

    def explode():
        raise RuntimeError("compositor not reachable")

    ad = Adapter()
    monkeypatch.setattr(ad, "_config_path", lambda: cfg)
    monkeypatch.setattr(ad, "_reload", explode)

    assert ad.register("dictate", "Ctrl+Alt+W") is False
