"""Bounded screen sampling, inference, and input-transparent Windows overlays."""
from __future__ import annotations

import ctypes
import time
from threading import Event

from PIL import Image
from PySide6.QtCore import QThread, Signal, Qt, QRect
from PySide6.QtGui import QImage, QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget

from .core import Detector, Box, censor_image


def qimage(image: Image.Image) -> QImage:
    rgb = image.convert("RGB")
    return QImage(rgb.tobytes(), rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888).copy()


class CaptureThread(QThread):
    result = Signal(object, int, int)
    failure = Signal(str)

    def __init__(self, settings: dict, monitor_ids: list[int]):
        super().__init__()
        self.settings = dict(settings)
        self.monitor_ids = monitor_ids
        self.stop_event = Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        import mss
        try:
            detector = Detector()
            interval = {"Low": .35, "Medium": .15, "High": .066, "Ultra": 0}[self.settings["preset"]]
            frames = 0
            with mss.mss() as screen:
                while not self.stop_event.is_set():
                    started = time.monotonic()
                    results = []
                    for monitor_id in self.monitor_ids:
                        if self.stop_event.is_set():
                            break
                        monitor = screen.monitors[monitor_id]
                        shot = screen.grab(monitor)
                        frame = Image.frombytes("RGB", shot.size, shot.rgb)
                        boxes = detector.detect(frame, self.settings)
                        patches = []
                        if self.settings["style"] in ("Mosaic", "Blur", "Custom image") and not self.settings["inverse"]:
                            custom = None
                            if self.settings["style"] == "Custom image" and self.settings["custom_image"]:
                                try:
                                    with Image.open(self.settings["custom_image"]) as file:
                                        custom = file.convert("RGB")
                                except (OSError, ValueError):
                                    pass
                            for box in boxes:
                                rect = (box.left, box.top, box.right, box.bottom)
                                part = frame.crop(rect)
                                local = Box(0, 0, part.width, part.height, box.score, box.category)
                                patches.append(qimage(censor_image(part, [local], self.settings, custom)))
                        results.append((monitor_id, boxes, patches, frame.size))
                        frames += 1
                    if self.stop_event.is_set():
                        break
                    self.result.emit(results, frames, round((time.monotonic()-started)*1000))
                    self.stop_event.wait(max(.025, interval-(time.monotonic()-started)))
        except Exception as exc:
            self.failure.emit(f"Protection stopped: {type(exc).__name__}: {exc}")


class Overlay(QWidget):
    def __init__(self, screen):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(screen.geometry())
        self.screen = screen
        self.boxes = []
        self.patches = []
        self.source_size = (1, 1)
        self.settings = {}

    def activate(self):
        self.show()
        # Exclude this window from supported Windows capture paths to avoid feedback.
        hwnd = int(self.winId())
        user32 = ctypes.windll.user32
        user32.GetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int)
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_long)
        user32.SetWindowLongW.restype = ctypes.c_long
        user32.SetWindowDisplayAffinity.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        user32.SetWindowDisplayAffinity.restype = ctypes.c_bool
        handle = ctypes.c_void_p(hwnd)
        style = user32.GetWindowLongW(handle, -20)
        user32.SetWindowLongW(handle, -20, style | 0x20 | 0x80 | 0x08000000)  # transparent, tool, no-activate
        if not user32.SetWindowDisplayAffinity(handle, 0x11):  # WDA_EXCLUDEFROMCAPTURE
            self.hide()
            raise RuntimeError("Windows could not exclude the overlay from screen capture. Windows 10 version 2004 or newer is required.")

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
            for box in self.boxes:
                holes.addRect(box.left*sx, box.top*sy, (box.right-box.left)*sx, (box.bottom-box.top)*sy)
            painter.fillPath(whole.subtracted(holes), color)
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
