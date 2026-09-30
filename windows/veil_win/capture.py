"""Bounded screen sampling, inference, and input-transparent Windows overlays."""
from __future__ import annotations

import ctypes
import logging
import time
from threading import Event, Lock

from PIL import Image
from PySide6.QtCore import QThread, Signal, Qt, QRect
from PySide6.QtGui import QImage, QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget

from .core import Detector, Box, censor_image

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

    def set_settings(self, settings):
        with self.lock:
            self.settings = dict(settings)
            self.reload_custom = True

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
            with mss.mss() as screen:
                LOG.info("Capture started: monitors=%s rectangles=%s", self.monitor_ids,
                         [screen.monitors[i] for i in self.monitor_ids])
                while not self.stop_event.is_set():
                    with self.lock:
                        settings = dict(self.settings)
                        if self.reload_custom:
                            custom_path = None
                            self.reload_custom = False
                    interval = {"Low": .35, "Medium": .15, "High": .066, "Ultra": 0}[settings["preset"]]
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
                        # Decode BGRA directly; avoid MSS's additional full-frame RGB buffer.
                        frame = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                        boxes = detector.detect(frame, settings, tiled=True, cancelled=self.stop_event.is_set)
                        patches = []
                        if settings["style"] in ("Mosaic", "Blur", "Custom image") and not settings["inverse"]:
                            for box in boxes:
                                rect = (box.left, box.top, box.right, box.bottom)
                                part = frame.crop(rect)
                                local = Box(0, 0, part.width, part.height, box.score, box.category)
                                patches.append(qimage(censor_image(part, [local], settings, custom)))
                        results.append((monitor_id, boxes, patches, frame.size))
                        frames += 1
                    if self.stop_event.is_set():
                        break
                    self.publish((results, frames, round((time.monotonic()-started)*1000), settings))
                    self.stop_event.wait(max(.025, interval-(time.monotonic()-started)))
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

    def update_result(self, boxes, patches, source_size, settings):
        self.boxes, self.patches = boxes, patches
        self.source_size, self.settings = source_size, dict(settings)
        self.update()

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
            if style in ("Mosaic", "Blur", "Custom image") and index < len(self.patches):
                painter.drawImage(QRect(*rect), self.patches[index])
            elif style != "Outline":
                painter.fillRect(*rect, color)
            if style in ("Mosaic", "Outline"):
                painter.setPen(QPen(QColor(self.settings["border_color"]), 3))
                painter.drawRect(round(x), round(y), max(1, round(w)-1), max(1, round(h)-1))
            if style == "Labeled":
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(round(x)+8, round(y)+22, self.settings["label"][:32])
        painter.end()
