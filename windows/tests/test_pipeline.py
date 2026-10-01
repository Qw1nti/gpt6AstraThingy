import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect
from veil_win.app import MainWindow
from veil_win.capture import CaptureThread, Overlay, qimage
from veil_win.core import Box
from veil_win.displays import match_screens
from veil_win.settings import DEFAULT
from veil_win.scanning import ScanTiming
from PIL import Image

APP = QApplication.instance() or QApplication([])


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"APPDATA": self.directory.name})
        self.env.start()

    def tearDown(self):
        APP.processEvents()
        self.env.stop()
        self.directory.cleanup()

    def test_latest_result_replaces_unconsumed_frames(self):
        worker = CaptureThread(DEFAULT, [1])
        notices = []
        worker.result.connect(lambda: notices.append(True))
        worker.publish(("old",))
        worker.publish(("new",))
        self.assertEqual(len(notices), 1)
        self.assertEqual(worker.take_result(), ("new",))
        worker.publish(("next",))
        self.assertEqual(len(notices), 2)

    def test_stale_worker_cannot_update_or_stop_new_session(self):
        with patch.object(MainWindow, "_monitors", return_value=[]):
            window = MainWindow()
            old, current = CaptureThread(DEFAULT, [1]), CaptureThread(DEFAULT, [1])
            window.worker = current
            old.result.connect(window._capture_result)
            old.failure.connect(window._capture_failed)
            old.publish(([], 999, 0, DEFAULT, ScanTiming(0, None)))
            old.failure.emit("Old failure")
            self.assertIs(window.worker, current)
            self.assertEqual(window.frames, 0)
            current.result.connect(window._capture_result)
            current.publish(([], 2, 5, DEFAULT, ScanTiming(5, 6.7)))
            self.assertEqual(window.frames, 2)
            self.assertIn("no selected categories", window.status)
            window.worker = None
            window.close()

    def test_scan_slider_applies_live_and_survives_reopening(self):
        with patch.object(MainWindow, "_monitors", return_value=[]):
            window = MainWindow()
            worker = CaptureThread(DEFAULT, [1])
            window.worker = worker
            window.scan_interval_slider.setValue(250)
            self.assertIs(window.worker, worker)
            self.assertEqual(worker.settings["scan_interval_ms"], 250)
            self.assertIn("4.0 scans/sec", window.scan_interval_label.text())
            self.assertTrue(window.interval_save_timer.isActive())
            window.worker = None
            window.close()
            reopened = MainWindow()
            self.assertEqual(reopened.scan_interval_slider.value(), 250)
            reopened.close()

    def test_scan_feedback_reports_processing_limit(self):
        with patch.object(MainWindow, "_monitors", return_value=[]):
            window = MainWindow()
            worker = CaptureThread({**DEFAULT, "scan_interval_ms": 50}, [1])
            window.worker = worker
            worker.result.connect(window._capture_result)
            worker.publish(([], 3, 120, worker.settings, ScanTiming(120, 8)))
            self.assertIn("8.0 scans/sec", window.home_scan_feedback.text())
            self.assertIn("rate is limited", window.home_scan_feedback.text())
            window.worker = None
            window.close()

    def test_live_settings_apply_without_detector_restart(self):
        with patch.object(MainWindow, "_monitors", return_value=[]):
            window = MainWindow()
            worker = CaptureThread(DEFAULT, [1])
            window.worker = worker
            window._changed(categories=[1, 12], style="Outline", confidence=30)
            self.assertIs(window.worker, worker)
            self.assertEqual(worker.settings["categories"], [1, 12])
            self.assertEqual(worker.settings["style"], "Outline")
            self.assertEqual(worker.settings["confidence"], 30)
            window.worker = None
            window.close()

    def test_renderer_scales_physical_capture_and_preserves_inverse_union(self):
        overlay = Overlay(APP.primaryScreen())
        overlay.resize(200, 100)
        box = Box(100, 50, 300, 150, .9, 1)
        overlay.update_result([box], [], (400, 200), DEFAULT)
        image = overlay.grab().toImage()
        self.assertEqual(image.pixelColor(100, 50).name(), DEFAULT["color"])
        self.assertEqual(image.pixelColor(5, 5).alpha(), 0)
        overlay.update_result([box, Box(150, 50, 350, 150, .8, 1)], [], (400, 200),
                              {**DEFAULT, "inverse": True})
        image = overlay.grab().toImage()
        self.assertEqual(image.pixelColor(100, 50).alpha(), 0)
        self.assertEqual(image.pixelColor(5, 5).name(), DEFAULT["color"])
        overlay.update_result([box], [qimage(Image.new("RGB", (200, 100), "#00ff00"))],
                              (400, 200), {**DEFAULT, "style": "Blur"})
        self.assertEqual(overlay.grab().toImage().pixelColor(100, 50).name(), "#00ff00")
        overlay.close()

    def test_monitor_identity_with_equal_sizes_and_mixed_scaling(self):
        class Screen:
            def __init__(self, name): self.device = name
            def name(self): return self.device
            def geometry(self):
                return QRect(0, 0, 1920, 1080) if self.device.endswith("1") else QRect(3840, 0, 3840, 2160)
            def size(self): return self.geometry().size()
            def devicePixelRatio(self): return 2 if self.device.endswith("1") else 1
        first, second = Screen("\\\\.\\DISPLAY1"), Screen("\\\\.\\DISPLAY2")
        monitors = {1: dict(left=3840, top=0, width=3840, height=2160),
                    2: dict(left=0, top=0, width=3840, height=2160)}
        devices = {(0, 0, 3840, 2160): "\\\\.\\DISPLAY1",
                   (3840, 0, 3840, 2160): "\\\\.\\DISPLAY2"}
        matched = match_screens(monitors, [first, second], devices)
        self.assertIs(matched[1], second)
        self.assertIs(matched[2], first)
        with self.assertRaises(RuntimeError):
            match_screens(monitors, [first], devices)

    def test_single_virtual_display_can_have_an_alias(self):
        class Screen:
            def name(self): return "Virtual desktop"
        screen = Screen()
        monitors = {1: dict(left=0, top=0, width=1024, height=768)}
        self.assertIs(match_screens(monitors, [screen], {(0, 0, 1024, 768): "DISPLAY1"})[1], screen)
