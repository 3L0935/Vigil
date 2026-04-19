"""GNOME adapter — parse/format helpers + subprocess call shape."""

from unittest.mock import patch

import hotkey.gnome as gnome


# ── combo conversion ────────────────────────────────────────────────────

def test_combo_ctrl_alt_letter():
    assert gnome._to_gnome_combo("Ctrl+Alt+W") == "<Ctrl><Alt>w"


def test_combo_super_key():
    assert gnome._to_gnome_combo("Super+Space") == "<Super>Space"


def test_combo_altgr_maps_to_alt():
    # AltGr is Alt for binding purposes.
    assert gnome._to_gnome_combo("AltGr+R") == "<Alt>r"


# ── list parsing ────────────────────────────────────────────────────────

def test_parse_empty_list():
    assert gnome._parse_gsettings_list("@as []") == []
    assert gnome._parse_gsettings_list("[]") == []


def test_parse_single_entry():
    s = "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/a/']"
    assert gnome._parse_gsettings_list(s) == [
        "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/a/",
    ]


def test_parse_multi_entry():
    s = "['/foo/', '/bar/']"
    assert gnome._parse_gsettings_list(s) == ["/foo/", "/bar/"]


def test_parse_garbage_returns_empty():
    assert gnome._parse_gsettings_list("not-a-list") == []


def test_format_round_trip():
    items = ["/a/", "/b/"]
    assert gnome._format_gsettings_list(items) == "['/a/', '/b/']"


# ── register: subprocess shape ───────────────────────────────────────────

def test_register_issues_expected_gsettings_calls():
    ad = gnome.GnomeAdapter()
    with patch("hotkey.gnome.subprocess.check_call") as call_mock, \
         patch("hotkey.gnome.subprocess.check_output", return_value="@as []"):
        ok = ad.register("dictate", "Ctrl+Alt+W",
                         command=["vigil-trigger", "dictate"])
    assert ok is True
    # 4 check_calls total: name, command, binding, list update.
    assert call_mock.call_count == 4
    path = ad._path_for("dictate")
    schema = ad._item_schema("dictate")
    first_three = [c.args[0] for c in call_mock.call_args_list[:3]]
    assert first_three == [
        ["gsettings", "set", schema, "name", "Vigil: dictate"],
        ["gsettings", "set", schema, "command", "vigil-trigger dictate"],
        ["gsettings", "set", schema, "binding", "<Ctrl><Alt>w"],
    ]
    # final list update includes the new path
    last = call_mock.call_args_list[3].args[0]
    assert last[:4] == ["gsettings", "set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings"]
    assert path in last[4]


def test_register_idempotent_when_path_already_listed():
    ad = gnome.GnomeAdapter()
    path = ad._path_for("dictate")
    existing = f"['{path}']"
    with patch("hotkey.gnome.subprocess.check_call") as call_mock, \
         patch("hotkey.gnome.subprocess.check_output", return_value=existing):
        ad.register("dictate", "Ctrl+Alt+W")
    # Only 3 calls: name/command/binding. No list update because the path is already in.
    assert call_mock.call_count == 3


def test_unregister_removes_path_and_resets_keys():
    ad = gnome.GnomeAdapter()
    path = ad._path_for("dictate")
    existing = f"['{path}', '/other/']"
    with patch("hotkey.gnome.subprocess.check_call") as check_mock, \
         patch("hotkey.gnome.subprocess.call") as plain_mock, \
         patch("hotkey.gnome.subprocess.check_output", return_value=existing):
        ok = ad.unregister("dictate")
    assert ok is True
    last = check_mock.call_args_list[-1].args[0]
    assert "/other/" in last[4]
    assert path not in last[4]
    assert plain_mock.call_count == 3  # reset name/command/binding


def test_list_registered_filters_vigil_paths():
    ad = gnome.GnomeAdapter()
    raw = (
        "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vigil-dictate/', "
        "'/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/']"
    )
    with patch("hotkey.gnome.subprocess.check_output", return_value=raw):
        assert ad.list_registered() == ["dictate"]


def test_is_available_checks_gsettings_binary():
    ad = gnome.GnomeAdapter()
    with patch("hotkey.gnome.shutil.which", return_value="/usr/bin/gsettings"):
        assert ad.is_available() is True
    with patch("hotkey.gnome.shutil.which", return_value=None):
        assert ad.is_available() is False
