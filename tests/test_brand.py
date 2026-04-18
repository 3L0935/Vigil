# tests/test_brand.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import brand


def test_render_vigil_eye_size_idle():
    img = brand.render_vigil_eye(size=64, idle=True)
    assert img.size == (64, 64)
    assert img.mode == "RGBA"


def test_render_vigil_eye_size_recording():
    img = brand.render_vigil_eye(size=64, idle=False)
    assert img.size == (64, 64)
    assert img.mode == "RGBA"


def test_render_vigil_eye_no_almond_small():
    # At size < 48, almond is suppressed
    img = brand.render_vigil_eye(size=32, idle=True)
    assert img.size == (32, 32)


def test_make_tray_icon_idle():
    img = brand.make_tray_icon(recording=False)
    assert img.size == (64, 64)


def test_make_tray_icon_recording():
    img = brand.make_tray_icon(recording=True)
    assert img.size == (64, 64)


def test_generate_app_icon():
    img = brand.generate_app_icon(128)
    assert img.size == (128, 128)
    assert img.mode == "RGBA"


def test_generate_banner():
    img = brand.generate_banner()
    assert img.size == (1280, 640)
