from PySide6.QtCore import QRect

from tools.overlay_probe import ANCHORS, anchor_position


def test_all_nine_anchors_stay_inside_available_geometry():
    rect = QRect(100, 50, 1000, 700)
    positions = {anchor: anchor_position(rect, 252, 50, anchor) for anchor in ANCHORS}

    assert len(positions) == 9
    assert len(set(positions.values())) == 9
    assert positions["top-left"] == (124, 74)
    assert positions["bottom-right"] == (824, 676)
    for x, y in positions.values():
        assert rect.left() <= x < rect.right()
        assert rect.top() <= y < rect.bottom()
