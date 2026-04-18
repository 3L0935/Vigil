import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import theme as T


def test_accent_is_cyan():
    assert T.ACCENT == "#00d4ff"


def test_fg_not_pure_white():
    assert T.FG == "#e8eaf0"


def test_bg_deep_not_black():
    assert T.BG_DEEP == "#03030a"


def test_border_is_cyan_tinted():
    assert T.BORDER == "#0d1a1f"


def test_semantic_colors_unchanged():
    assert T.RED == "#ff4444"
    assert T.GREEN == "#55cc77"
    assert T.YELLOW == "#ffaa00"
