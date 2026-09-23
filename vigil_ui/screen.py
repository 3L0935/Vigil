"""Track the screen of the active desktop window on X11/XWayland."""

import re
import subprocess
import threading

from logger import log


class ActiveScreenTracker:
    def __init__(self):
        self._rect = None
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="vigil-active-screen")

    def start(self):
        self._thread.start()

    def get_rect(self):
        with self._lock:
            return self._rect

    def _run(self):
        try:
            from Xlib import X, display
            connection = display.Display()
            root = connection.screen().root
            atom = connection.intern_atom("_NET_ACTIVE_WINDOW")
            root.change_attributes(event_mask=X.PropertyChangeMask)
            connection.flush()
            while True:
                self._sample(connection, root, atom)
                event = connection.next_event()
                if event.type != X.PropertyNotify or getattr(event, "atom", None) != atom:
                    continue
        except Exception as exc:
            log.debug("Active screen tracker unavailable: %s", type(exc).__name__)

    def _sample(self, connection, root, atom):
        try:
            prop = root.get_full_property(atom, X.AnyPropertyType)
            wid = int(prop.value[0]) if prop is not None and len(prop.value) else 0
            if not wid:
                return
            window = connection.create_resource_object("window", wid)
            geom = window.get_geometry()
            pos = root.translate_coords(window, 0, 0)
            cx, cy = pos.x + geom.width // 2, pos.y + geom.height // 2
            output = subprocess.check_output(["xrandr", "--query"], text=True,
                                             stderr=subprocess.DEVNULL, timeout=2)
            for line in output.splitlines():
                match = re.search(r"\bconnected\b.*?(\d+)x(\d+)\+(\d+)\+(\d+)", line)
                if match:
                    width, height, x, y = map(int, match.groups())
                    if x <= cx < x + width and y <= cy < y + height:
                        with self._lock:
                            self._rect = (x, y, width, height)
                        return
        except Exception:
            return
