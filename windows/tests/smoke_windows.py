"""Exercise real Windows display mapping, GDI capture, inference and overlays.

Requires an interactive Windows desktop; never saves screen captures.
"""
import ctypes
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

os.environ["APPDATA"] = tempfile.mkdtemp(prefix="veil-desktop-")
os.environ.pop("QT_QPA_PLATFORM", None)

from PIL import Image
import mss
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
from veil_win.app import MainWindow
from veil_win.capture import qimage
from veil_win.diagnostics import configure_logging

configure_logging()
ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
app = QApplication([])
screen = app.primaryScreen()
target = QLabel()
target.setWindowFlags(Qt.WindowType.FramelessWindowHint)
target.setGeometry(screen.geometry())
target.setStyleSheet("background:#888888")
target.setAlignment(Qt.AlignmentFlag.AlignCenter)
with Image.open(Path(__file__).parent / "fixtures" / "astronaut.jpg") as file:
    portrait = file.convert("RGB")
portrait.thumbnail((min(512, screen.size().width()), min(512, screen.size().height())))
target.setPixmap(QPixmap.fromImage(qimage(portrait)))
target.show()


def until(condition, seconds=20):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return
        time.sleep(.02)
    raise AssertionError("Timed out waiting for native desktop pipeline")


def warning(parent, title, message):
    raise AssertionError(f"{title}: {message}")


window = MainWindow()
try:
    app.processEvents()
    time.sleep(.2)  # Let the compositor present the static fixture.
    with mss.mss() as capture:
        before = [capture.grab(m).pixel(m['width']//2, m['height']//2)
                  for m in capture.monitors[1:]]
    with patch.object(QMessageBox, "warning", side_effect=warning):
        window.test_overlay()
    app.processEvents()
    time.sleep(.2)
    user32 = ctypes.windll.user32
    user32.IsWindowVisible.argtypes = (ctypes.c_void_p,)
    user32.GetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int)
    for overlay in window.overlays.values():
        assert user32.IsWindowVisible(ctypes.c_void_p(int(overlay.winId())))
        style = user32.GetWindowLongW(ctypes.c_void_p(int(overlay.winId())), -20)
        assert style & 0x20 and style & 0x08000000, "Overlay must be click-through and non-activating"
        image = overlay.grab().toImage()
        assert image.pixelColor(image.width()//2, image.height()//2).name() == "#e53935"
    with mss.mss() as capture:
        after = [capture.grab(m).pixel(m['width']//2, m['height']//2)
                 for m in capture.monitors[1:]]
    assert before == after, "Overlay polluted or blacked out the captured desktop"
    window.stop_protection()
    window.store.update(categories=[1, 12], style="Solid Box", coverage=0)
    with patch.object(QMessageBox, "warning", side_effect=warning):
        window.start_protection()
    until(lambda: window.worker is None or any(o.boxes for o in window.overlays.values()))
    assert window.worker is not None, window.status
    overlay = next(o for o in window.overlays.values() if o.boxes)
    box = overlay.boxes[0]
    image = overlay.grab().toImage()
    x = round((box.left+box.right)/2*image.width()/overlay.source_size[0])
    y = round((box.top+box.bottom)/2*image.height()/overlay.source_size[1])
    assert image.pixelColor(x, y).name() == "#e53935", "Detected face did not reach the overlay renderer"
    window._changed(categories=[])
    until(lambda: all(not o.boxes for o in window.overlays.values()))
    window._changed(categories=[1, 12])
    until(lambda: any(o.boxes for o in window.overlays.values()))
    worker = window.worker
    window.scan_interval_slider.setValue(250)
    window._changed(style="Pixelated Blur", pixel_size=24)
    until(lambda: any(o.boxes and o.patches and o.settings["style"] == "Pixelated Blur"
                      and o.settings["scan_interval_ms"] == 250 for o in window.overlays.values()))
    assert window.worker is worker, "Changing scan rate or pixelation restarted detection"
    until(lambda: "scans/sec" in window.scan_feedback)
    print("Measured Windows runner timing (not owner PC):", window.scan_feedback)
    print("Native Windows pipeline passed: mapping, visible window, click-through styles, "
          "capture exclusion, real face detection, rendered pixels, live interval and pixelated blur.")
finally:
    window.stop_protection()
    until(lambda: not window.retired_workers)
    window.close()
    target.close()
    app.quit()
