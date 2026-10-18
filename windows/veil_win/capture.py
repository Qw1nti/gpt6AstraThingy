"""Bounded screen sampling, inference, and input-transparent Windows overlays."""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import logging
import math
import time
from threading import Event, Lock

from PIL import Image
from PySide6.QtCore import QThread, Signal, Qt, QRect, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QRegion
from PySide6.QtWidgets import QWidget

from .core import Detector
from .effects import PatchRenderer, qimage
from .scanning import ScanMeter, ScanTiming, scan_delay
from .tracking import MotionTracker

LOG = logging.getLogger(__name__)


def policy(settings):
    return tuple((key, tuple(value) if isinstance(value, list) else value)
                 for key, value in sorted(settings.items()) if key not in ("scan_interval_ms", "monitor"))


@dataclass
class CaptureBatch:
    monitors: list
    frames: int
    elapsed: int
    settings: dict
    timing: ScanTiming
    revision: int = 0
    complete: bool = True


class CaptureThread(QThread):
    result = Signal()
    failure = Signal(str)

    def __init__(self, settings: dict, monitor_ids: list[int]):
        super().__init__()
        self.settings = dict(settings)
        self.monitor_ids = monitor_ids
        self.stop_event = Event()
        self.wake_event = Event()
        self.lock = Lock()
        self.latest = None
        self.notification_pending = False
        self.reload_custom = False
        self.revision = 0

    def set_settings(self, settings, *, reload_custom=False):
        with self.lock:
            if policy(settings) != policy(self.settings) or reload_custom:
                self.revision += 1
                self.latest = None
            self.settings = dict(settings)
            self.reload_custom = self.reload_custom or reload_custom
        self.wake_event.set()

    def current_settings(self):
        with self.lock:
            return dict(self.settings)

    def obsolete(self, revision):
        with self.lock:
            return self.stop_event.is_set() or revision != self.revision

    def take_result(self):
        with self.lock:
            result, self.latest = self.latest, None
            self.notification_pending = False
            return result

    def publish(self, result):
        with self.lock:
            if result.revision != self.revision:
                return
            if self.latest is not None:
                # Retain one newest result per display, even if the UI is busy.
                merged = {item[0]: item for item in self.latest.monitors}
                merged.update({item[0]: item for item in result.monitors})
                result.monitors = list(merged.values())
                if self.latest.complete and not result.complete:
                    result.elapsed, result.timing, result.complete = self.latest.elapsed, self.latest.timing, True
            self.latest = result
            notify = not self.notification_pending
            self.notification_pending = True
        if notify:
            self.result.emit()

    def stop(self):
        self.stop_event.set()
        self.wake_event.set()

    def run(self):
        import mss
        try:
            detector = Detector()
            renderer = PatchRenderer()
            custom_path, custom = None, None
            frames = 0
            meter, previous_interval = ScanMeter(), None
            timing = ScanTiming(0, None)
            with mss.mss() as screen:
                LOG.info("Capture started: monitors=%s rectangles=%s", self.monitor_ids,
                         [screen.monitors[i] for i in self.monitor_ids])
                while not self.stop_event.is_set():
                    self.wake_event.clear()
                    with self.lock:
                        settings, revision = dict(self.settings), self.revision
                        if self.reload_custom:
                            custom_path = None
                            self.reload_custom = False
                    cancelled = lambda: self.obsolete(revision)
                    interval_ms = settings["scan_interval_ms"]
                    if interval_ms != previous_interval:
                        meter, previous_interval = ScanMeter(), interval_ms
                        timing = ScanTiming(0, None)
                    path = settings["custom_image"] if settings["style"] == "Custom image" else ""
                    if path != custom_path:
                        custom_path, custom = path, None
                        if path:
                            try:
                                with Image.open(path) as file:
                                    custom = file.convert("RGB")
                            except (OSError, ValueError):
                                LOG.exception("Custom mask unavailable; using solid coverage")
                    # Model initialization must not age the first captured frame.
                    detector.prepare(settings, cancelled=cancelled)
                    if cancelled():
                        continue
                    started = time.monotonic()
                    for index, monitor_id in enumerate(self.monitor_ids):
                        if cancelled():
                            break
                        monitor = screen.monitors[monitor_id]
                        captured_at = time.monotonic()
                        shot = screen.grab(monitor)
                        frame = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                        boxes = detector.detect(frame, settings, tiled=True, cancelled=cancelled)
                        if cancelled():
                            break
                        patches = renderer.render(frame, boxes, settings, custom)
                        if cancelled():
                            break
                        frames += 1
                        finished = time.monotonic()
                        complete = index == len(self.monitor_ids)-1
                        if complete:
                            timing = meter.observe(started, finished)
                        # Deliver this screen before starting inference on the next.
                        self.publish(CaptureBatch([(monitor_id, boxes, patches, frame.size, captured_at)],
                                     frames, round((finished-started)*1000), settings, timing, revision, complete))
                    self.wake_event.wait(scan_delay(interval_ms, time.monotonic()-started))
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
        self.last_received = None
        self.result_period = 0
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(16)
        self.motion_timer.setTimerType(Qt.TimerType.PreciseTimer)
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
        old_boxes = self.boxes
        key = (source_size, tuple(settings["categories"]), settings["coverage"], settings["confidence"],
               settings["style"], settings["inverse"], settings["pixel_size"], settings["custom_image"],
               settings["color"], settings["border_color"], settings["label"], settings.get("motion_prediction", True))
        reset = key != self.tracking_key
        if reset:
            self.tracker, self.tracking_key = MotionTracker(), key
            self.last_received, self.result_period = None, 0
        self.source_size, self.settings = source_size, dict(settings)
        now = time.monotonic()
        if self.last_received is not None:
            period = max(0, now-self.last_received)
            # Respond to a slow cycle immediately, recover gradually afterward.
            self.result_period = max(period, self.result_period*.8)
        self.last_received = now
        if settings.get("motion_prediction", True):
            self.tracker.update(boxes, patches, now if captured_at is None else captured_at,
                                now, source_size, self._hold_time())
            self.boxes, self.patches = self.tracker.render(now, source_size, self._hold_time())
            if self.tracker.tracks:
                self.motion_timer.start()
        else:
            self.motion_timer.stop()
            self.boxes, self.patches = boxes, patches
        self._repaint(old_boxes, reset)

    def _hold_time(self):
        period = max(self.settings.get("scan_interval_ms", 150)/1000, self.result_period)
        return max(.30, min(1.50, period*1.5))

    def _box_rect(self, box):
        sx, sy = self.width()/self.source_size[0], self.height()/self.source_size[1]
        left, top = math.floor(box.left*sx), math.floor(box.top*sy)
        right, bottom = math.ceil(box.right*sx), math.ceil(box.bottom*sy)
        return QRect(left, top, max(1, right-left), max(1, bottom-top))

    def _repaint(self, old_boxes, full=False):
        if full:
            self.update()
            return
        dirty = QRegion()
        for box in old_boxes + self.boxes:
            dirty |= QRegion(self._box_rect(box).adjusted(-3, -3, 3, 3))
        if not dirty.isEmpty():
            self.update(dirty)

    def restrict_categories(self, settings):
        """Remove disabled categories immediately, including held tracks."""
        categories = set(settings["categories"])
        def allowed(box):
            selected = box.category in categories or (box.category == 1 and 12 in categories)
            return selected and box.score >= settings["confidence"]/100
        old_boxes = self.boxes
        kept = [index for index, box in enumerate(self.boxes) if allowed(box)]
        self.boxes = [self.boxes[index] for index in kept]
        self.patches = [self.patches[index] if index < len(self.patches) else None for index in kept]
        self.tracker.tracks = [track for track in self.tracker.tracks if allowed(track.box)]
        self._repaint(old_boxes)

    def _animate(self):
        boxes, patches = self.tracker.render(time.monotonic(), self.source_size, self._hold_time())
        changed = boxes != self.boxes
        old_boxes = self.boxes
        self.boxes, self.patches = boxes, patches
        if changed:
            self._repaint(old_boxes)
        if not self.tracker.tracks:
            self.motion_timer.stop()

    def hideEvent(self, event):
        self.motion_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        if not self.settings:
            return
        painter = QPainter(self)
        painter.setClipRegion(event.region())
        # Explicitly erase the dirty alpha region, including old mask positions.
        # Translucent top-level windows may have WA_NoSystemBackground set.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
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
            target = self._box_rect(box)
            if not event.region().intersects(target.adjusted(-3, -3, 3, 3)):
                continue
            x, y, w, h = target.x(), target.y(), target.width(), target.height()
            rect = (x, y, w, h)
            style = self.settings["style"]
            if style in ("Mosaic", "Pixelated Blur", "Blur", "Custom image") and index < len(self.patches) and self.patches[index] is not None:
                painter.drawImage(QRect(*rect), self.patches[index])
            elif style != "Outline":
                painter.fillRect(*rect, color)
            if style in ("Mosaic", "Pixelated Blur", "Outline"):
                painter.setPen(QPen(QColor(self.settings["border_color"]), 3))
                painter.drawRect(round(x), round(y), max(1, round(w)-1), max(1, round(h)-1))
            if style == "Labeled":
                painter.save()
                painter.setClipRect(target, Qt.ClipOperation.IntersectClip)
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(round(x)+8, round(y)+22, self.settings["label"][:32])
                painter.restore()
        painter.end()
