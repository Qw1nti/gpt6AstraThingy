"""Bounded screen sampling, inference, and input-transparent Windows overlays."""
from __future__ import annotations

import ctypes
import logging
import time
from threading import Event, Lock

from PIL import Image
from PySide6.QtCore import QThread, Signal, Qt, QRect, QTimer
from PySide6.QtGui import QImage, QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget

from .core import Detector, Box, censor_image
from .scanning import ScanMeter, scan_delay
from .tracking import MotionTracker

LOG = logging.getLogger(__name__)


def qimage(image: Image.Image) -> QImage:
    rgb = image.convert("RGB")
    return QImage(rgb.tobytes(), rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888).copy()


class CaptureThread(QThread):
    result = Signal()
    failure = Signal(str)

    def __init__(self, settings: dict, monitor_ids: list[int]):
        super().__init__()
        self.settings = dict(settings)
        self.monitor_ids = monitor_ids
        self.stop_event = Event()
        self.lock = Lock()
        self.latest = None
        self.notification_pending = False
        self.reload_custom = False

    def set_settings(self, settings, *, reload_custom=False):
        with self.lock:
            self.settings = dict(settings)
            self.reload_custom = self.reload_custom or reload_custom

    def take_result(self):
        with self.lock:
            result, self.latest = self.latest, None
            self.notification_pending = False
            return result

    def publish(self, result):
        with self.lock:
            self.latest = result
            notify = not self.notification_pending
            self.notification_pending = True
        if notify:
            self.result.emit()

    def stop(self):
        self.stop_event.set()

    def run(self):
        import mss
        try:
            detector = Detector()
            custom_path, custom = None, None
            frames = 0
            meter, previous_interval = ScanMeter(), None
            with mss.mss() as screen:
                LOG.info("Capture started: monitors=%s rectangles=%s", self.monitor_ids,
                         [screen.monitors[i] for i in self.monitor_ids])
                while not self.stop_event.is_set():
                    with self.lock:
                        settings = dict(self.settings)
                        if self.reload_custom:
                            custom_path = None
                            self.reload_custom = False
                    interval_ms = settings["scan_interval_ms"]
                    if interval_ms != previous_interval:
                        meter, previous_interval = ScanMeter(), interval_ms
                    path = settings["custom_image"] if settings["style"] == "Custom image" else ""
                    if path != custom_path:
                        custom_path, custom = path, None
                        if path:
                            try:
                                with Image.open(path) as file:
                                    custom = file.convert("RGB")
                            except (OSError, ValueError):
                                LOG.exception("Custom mask unavailable; using solid coverage")
                    started = time.monotonic()
                    results = []
                    for monitor_id in self.monitor_ids:
                        if self.stop_event.is_set():
                            break
                        monitor = screen.monitors[monitor_id]
                        shot = screen.grab(monitor)
                        captured_at = time.monotonic()
                        # Decode BGRA directly; avoid MSS's additional full-frame RGB buffer.
                        frame = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                        boxes = detector.detect(frame, settings, tiled=True, cancelled=self.stop_event.is_set)
                        patches = []
                        if settings["style"] in ("Mosaic", "Pixelated Blur", "Blur", "Custom image") and not settings["inverse"]:
                            for box in boxes:
                                rect = (box.left, box.top, box.right, box.bottom)
                                part = frame.crop(rect)
                                local = Box(0, 0, part.width, part.height, box.score, box.category)
                                patches.append(qimage(censor_image(part, [local], settings, custom)))
                        results.append((monitor_id, boxes, patches, frame.size, captured_at))
                        frames += 1
                    if self.stop_event.is_set():
                        break
                    finished = time.monotonic()
                    self.publish((results, frames, round((finished-started)*1000), settings,
                                  meter.observe(started, finished)))
                    self.stop_event.wait(scan_delay(interval_ms, time.monotonic()-started))
        except Exception as exc:
            LOG.exception("Capture failed")
            self.failure.emit(f"Protection stopped: {type(exc).__name__}: {exc}")


class Overlay(QWidget):
    def __init__(self, screen):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.winId()  # Create the native window before associating its display.
        self.windowHandle().setScreen(screen)
        self.setGeometry(screen.geometry())
        self.boxes = []
        self.patches = []
        self.source_size = (1, 1)
        self.settings = {}
        self.tracker = MotionTracker()
        self.tracking_key = None
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(33)
        self.motion_timer.timeout.connect(self._animate)

    def activate(self):
        self.show()
        # Exclude this window from supported Windows capture paths to avoid feedback.
        hwnd = int(self.winId())
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int)
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_long)
        user32.SetWindowLongW.restype = ctypes.c_long
        user32.SetWindowDisplayAffinity.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        user32.SetWindowDisplayAffinity.restype = ctypes.c_bool
        handle = ctypes.c_void_p(hwnd)
        style = user32.GetWindowLongW(handle, -20)
        ctypes.set_last_error(0)
        previous = user32.SetWindowLongW(handle, -20, style | 0x20 | 0x80 | 0x08000000)
        if not previous and ctypes.get_last_error():
            self.hide()
            raise ctypes.WinError(ctypes.get_last_error())
        if not user32.SetWindowDisplayAffinity(handle, 0x11):  # WDA_EXCLUDEFROMCAPTURE
            self.hide()
            error = ctypes.get_last_error()
            raise RuntimeError(f"Windows could not exclude the overlay from screen capture (error {error}). Windows 10 version 2004 or newer is required.")
        LOG.info("Overlay activated: handle=%s geometry=%s DPR=%s", hwnd, self.geometry(), self.devicePixelRatioF())

    def update_result(self, boxes, patches, source_size, settings, captured_at=None):
        key = (source_size, tuple(settings["categories"]), settings["coverage"], settings["confidence"],
               settings["style"], settings["inverse"], settings["pixel_size"], settings["custom_image"],
               settings["color"], settings["border_color"], settings["label"], settings.get("motion_prediction", True))
        if key != self.tracking_key:
            self.tracker, self.tracking_key = MotionTracker(), key
        self.source_size, self.settings = source_size, dict(settings)
        if settings.get("motion_prediction", True):
            now = time.monotonic()
            self.tracker.update(boxes, patches, now if captured_at is None else captured_at,
                                now, source_size, self._hold_time())
            self.boxes, self.patches = self.tracker.render(now, source_size, self._hold_time())
            self.motion_timer.start()
        else:
            self.motion_timer.stop()
            self.boxes, self.patches = boxes, patches
        self.update()

    def _hold_time(self):
        return max(.30, min(.60, self.settings.get("scan_interval_ms", 150)/1000*1.5))

    def _animate(self):
        boxes, patches = self.tracker.render(time.monotonic(), self.source_size, self._hold_time())
        changed = boxes != self.boxes
        self.boxes, self.patches = boxes, patches
        if changed:
            self.update()
        if not self.tracker.tracks:
            self.motion_timer.stop()

    def hideEvent(self, event):
        self.motion_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        if not self.settings:
            return
        painter = QPainter(self)
        sx = self.width()/self.source_size[0]
        sy = self.height()/self.source_size[1]
        color = QColor(self.settings["color"])
        if self.settings["inverse"] and self.settings["style"] != "Outline":
            from PySide6.QtGui import QPainterPath
            whole = QPainterPath()
            whole.addRect(self.rect())
            holes = QPainterPath()
            holes.setFillRule(Qt.FillRule.WindingFill)
            for box in self.boxes:
                holes.addRect(box.left*sx, box.top*sy, (box.right-box.left)*sx, (box.bottom-box.top)*sy)
            painter.fillPath(whole.subtracted(holes), color)
            painter.end()
            return
        for index, box in enumerate(self.boxes):
            x, y = box.left*sx, box.top*sy
            w, h = (box.right-box.left)*sx, (box.bottom-box.top)*sy
            rect = (round(x), round(y), round(w), round(h))
            style = self.settings["style"]
            if style in ("Mosaic", "Pixelated Blur", "Blur", "Custom image") and index < len(self.patches) and self.patches[index] is not None:
                painter.drawImage(QRect(*rect), self.patches[index])
            elif style != "Outline":
                painter.fillRect(*rect, color)
            if style in ("Mosaic", "Pixelated Blur", "Outline"):
                painter.setPen(QPen(QColor(self.settings["border_color"]), 3))
                painter.drawRect(round(x), round(y), max(1, round(w)-1), max(1, round(h)-1))
            if style == "Labeled":
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(round(x)+8, round(y)+22, self.settings["label"][:32])
        painter.end()
