"""KWin blur only covers the two visible overlay surfaces."""

from vigil_ui.kwin_blur import _rounded_rectangles


class Surface:
    def __init__(self, x, y, width, height, radius):
        self._bounds = x, y, width, height, radius

    def x(self):
        return self._bounds[0]

    def y(self):
        return self._bounds[1]

    def width(self):
        return self._bounds[2]

    def height(self):
        return self._bounds[3]

    def property(self, key):
        assert key == "radius"
        return self._bounds[4]


def test_blur_rectangles_leave_the_card_pill_gap_clear():
    card = _rounded_rectangles(Surface(0, 0, 420, 188, 14), 1)
    pill = _rounded_rectangles(Surface(84, 200, 252, 50, 25), 1)

    assert all(y + height <= 188 for _, y, _, height in card)
    assert all(y >= 200 for _, y, _, _ in pill)
    assert card[0] == (14, 0, 392, 188)
    assert pill[0] == (109, 200, 202, 50)
