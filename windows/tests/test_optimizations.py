import gc
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from veil_win.app import MainWindow
from veil_win.capture import CaptureBatch, CaptureThread, Overlay
from veil_win.core import Box, Detector, censor_image
from veil_win.effects import PatchRenderer, qimage
from veil_win.faces import FaceDetector
from veil_win.scanning import ScanTiming
from veil_win.settings import DEFAULT
from veil_win.tracking import MotionTracker

APP = QApplication.instance() or QApplication([])


def packet(monitor, value, *, revision=0, complete=True):
    return CaptureBatch([(monitor, [value], [], (400, 200), 1)], value, 50, DEFAULT,
                        ScanTiming(50, 5), revision, complete)


class OptimizationTests(unittest.TestCase):
    def overlay(self):
        overlay = Overlay(APP.primaryScreen())
        self.addCleanup(overlay.close)
        return overlay

    def test_mailbox_keeps_newest_of_each_display_and_completed_timing(self):
        worker = CaptureThread(DEFAULT, [1, 2])
        notices = []
        worker.result.connect(lambda: notices.append(True))
        worker.publish(packet(1, 1, complete=False))
        worker.publish(packet(2, 2))
        worker.publish(packet(1, 3, complete=False))
        result = worker.take_result()
        self.assertEqual({item[0]: item[1] for item in result.monitors}, {1: [3], 2: [2]})
        self.assertTrue(result.complete)
        self.assertEqual(result.timing.work_ms, 50)
        self.assertEqual(len(notices), 1)

    def test_changed_policy_rejects_old_work_without_losing_pending_notification(self):
        worker = CaptureThread(DEFAULT, [1])
        notices = []
        worker.result.connect(lambda: notices.append(True))
        worker.publish(packet(1, 1))
        worker.set_settings({**DEFAULT, "categories": []})
        self.assertTrue(worker.wake_event.is_set())
        worker.publish(packet(1, 2))  # Obsolete revision.
        worker.publish(packet(1, 3, revision=worker.revision))
        self.assertEqual(worker.take_result().frames, 3)
        self.assertEqual(len(notices), 1)
        revision = worker.revision
        worker.set_settings({**worker.settings, "scan_interval_ms": 10})
        self.assertEqual(worker.revision, revision)
        worker.stop()
        self.assertTrue(worker.obsolete(revision))

    def test_capture_delivers_first_monitor_before_scanning_second(self):
        worker = CaptureThread(DEFAULT, [1, 2])
        packets = []
        shot = SimpleNamespace(size=(32, 32), bgra=bytes((10, 20, 30, 255))*32*32)

        class Screen:
            monitors = [{}, {"id": 1}, {"id": 2}]
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def grab(self, monitor):
                if monitor["id"] == 2:
                    self_test.assertEqual(packets[0].monitors[0][0], 1)
                    self_test.assertFalse(packets[0].complete)
                return shot

        def publish(result):
            packets.append(result)
            if result.complete:
                worker.stop()

        self_test = self
        with patch("mss.mss", return_value=Screen()), patch("veil_win.capture.Detector") as detector, patch.object(worker, "publish", side_effect=publish):
            detector.return_value.detect.return_value = []
            worker.run()
        self.assertEqual(len(packets), 2)
        self.assertTrue(packets[-1].complete)
        self.assertGreater(packets[0].monitors[0][4], 0)

    def test_live_patch_pixels_equal_previous_renderer(self):
        frame = Image.fromarray(np.random.default_rng(5).integers(0, 256, (100, 120, 3), dtype=np.uint8))
        box = Box(7, 9, 85, 81, .9, 1)
        custom = frame.resize((40, 40))
        renderer = PatchRenderer()
        for style in ("Blur", "Pixelated Blur", "Custom image"):
            settings = {**DEFAULT, "style": style}
            new = renderer.render(frame, [box], settings, custom)[0].convertToFormat(QImage.Format.Format_RGBA8888)
            part = frame.crop((box.left, box.top, box.right, box.bottom))
            expected = censor_image(part, [Box(0, 0, part.width, part.height, .9, 1)], settings, custom)
            actual = Image.frombytes("RGBA", part.size, bytes(new.constBits())).convert("RGB")
            self.assertEqual(actual.tobytes(), expected.tobytes(), style)
        self.assertEqual(renderer.render(frame, [box], {**DEFAULT, "style": "Custom image"}), [None])
        self.assertEqual(renderer.render(frame, [box], {**DEFAULT, "style": "Blur", "inverse": True}), [])

    def test_custom_cache_is_bounded_and_invalidated_and_qimage_owns_pixels(self):
        frame = Image.new("RGB", (100, 100))
        settings = {**DEFAULT, "style": "Custom image"}
        renderer = PatchRenderer(limit_bytes=1024)
        custom = Image.new("RGB", (30, 30), "red")
        box = Box(0, 0, 12, 12, .9, 1)
        first = renderer.render(frame, [box], settings, custom)[0]
        self.assertIs(renderer.render(frame, [box], settings, custom)[0], first)
        for edge in (13, 14, 30):
            renderer.render(frame, [Box(0, 0, edge, edge, .9, 1)], settings, custom)
            self.assertLessEqual(renderer.cache_bytes, 1024)
        fresh = renderer.render(frame, [box], settings, Image.new("RGB", (30, 30), "blue"))[0]
        self.assertEqual(fresh.pixelColor(0, 0).name(), "#0000ff")
        image = qimage(Image.new("RGB", (11, 9), "#123456"))
        gc.collect()
        self.assertEqual(image.pixelColor(10, 8).name(), "#123456")

    def test_body_tensor_matches_original_and_clears_padding_between_shapes(self):
        detector = Detector()
        recorded = []
        class Session:
            def run(self, _, inputs):
                recorded.append((id(inputs["input"]), inputs["input"].copy()))
                return [np.zeros((1, 22, 1), dtype=np.float32)]
        detector.session, detector.input_name = Session(), "input"
        for size in ((367, 123), (123, 367)):
            source = Image.new("RGBA", size, (25, 112, 201, 255))
            detector._detect_body(source, DEFAULT)
            edge = max(size)
            scaled = source.convert("RGB").resize(tuple(max(1, round(d*320/edge)) for d in size), Image.Resampling.BILINEAR)
            square = Image.new("RGB", (320, 320))
            square.paste(scaled)
            expected = np.ascontiguousarray(np.asarray(square, dtype=np.float32).transpose(2, 0, 1)[None]/255)
            np.testing.assert_array_equal(recorded[-1][1], expected)
        self.assertEqual(recorded[0][0], recorded[1][0])

    def test_face_buffer_reuse_clears_old_padding(self):
        detector = FaceDetector.__new__(FaceDetector)
        detector.input_name = "input"
        detector.names = [f"{kind}_{stride}" for kind in ("cls", "obj", "bbox") for stride in (8, 16, 32)]
        snapshots = []
        class Session:
            def run(self, _, inputs):
                data = inputs["input"]
                snapshots.append((id(data), data.copy()))
                h, w = data.shape[2:]
                return [np.zeros((1, w//int(name.split('_')[1])*(h//int(name.split('_')[1])), 4 if name.startswith('bbox') else 1), np.float32)
                        for name in detector.names]
        detector.session = Session()
        for size in ((63, 31), (50, 20), (100, 50)):
            detector._detect(Image.new("RGB", size, "white"), .45)
        self.assertEqual(snapshots[0][0], snapshots[1][0])
        self.assertFalse(snapshots[1][1][:, :, 20:, :].any())
        self.assertFalse(snapshots[1][1][:, :, :, 50:].any())
        self.assertNotEqual(snapshots[1][0], snapshots[2][0])

    def test_slow_scan_holds_until_next_result_but_still_expires(self):
        overlay = self.overlay()
        settings = {**DEFAULT, "scan_interval_ms": 1000}
        with patch("veil_win.capture.time.monotonic", return_value=1):
            overlay.update_result([Box(10, 10, 50, 50, .9, 1)], [], (400, 200), settings, 1)
        with patch("veil_win.capture.time.monotonic", return_value=2.1):
            overlay._animate()
            self.assertTrue(overlay.boxes)
            overlay.update_result([], [], (400, 200), settings, 2)
        with patch("veil_win.capture.time.monotonic", return_value=2.51):
            overlay._animate()
        self.assertFalse(overlay.boxes)
        self.assertLessEqual(overlay._hold_time(), 1.5)

    def test_partial_repaint_erases_old_pixels_and_keeps_unrelated_pixels(self):
        overlay = self.overlay()
        overlay.resize(500, 300)
        settings = {**DEFAULT, "motion_prediction": False}
        overlay.update_result([Box(10, 10, 50, 50, .9, 1)], [], (500, 300), settings)
        backing = QImage(500, 300, QImage.Format.Format_ARGB32_Premultiplied)
        backing.fill(0)
        overlay.render(backing)
        self.assertEqual(backing.pixelColor(20, 20).name(), DEFAULT["color"])
        backing.setPixelColor(450, 250, "blue")
        with patch.object(overlay, "update") as update:
            overlay.update_result([Box(200, 10, 240, 50, .9, 1)], [], (500, 300), settings)
        dirty = update.call_args.args[0]
        self.assertLess(dirty.boundingRect().width()*dirty.boundingRect().height(), 500*300/4)
        painter = QPainter(backing)
        overlay.render(painter, dirty.boundingRect().topLeft(), dirty)
        painter.end()
        self.assertEqual(backing.pixelColor(20, 20).alpha(), 0)
        self.assertEqual(backing.pixelColor(210, 20).name(), DEFAULT["color"])
        self.assertEqual(backing.pixelColor(450, 250).name(), "#0000ff")

    def test_fractional_display_scaling_rounds_mask_coverage_outward(self):
        overlay = self.overlay()
        overlay.resize(103, 103)
        overlay.source_size = (200, 200)
        rect = overlay._box_rect(Box(1, 1, 3, 3, .9, 1))
        self.assertEqual((rect.x(), rect.y(), rect.width(), rect.height()), (0, 0, 2, 2))

    def test_disabled_categories_are_removed_from_held_tracks_immediately(self):
        overlay = self.overlay()
        overlay.update_result([Box(10, 10, 50, 50, .9, 1)], [], (400, 200), DEFAULT)
        overlay.restrict_categories({**DEFAULT, "categories": []})
        overlay._animate()
        self.assertFalse(overlay.boxes)
        self.assertFalse(overlay.tracker.tracks)

    def test_live_category_change_cannot_reapply_queued_old_detections(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"APPDATA": directory}), patch.object(MainWindow, "_monitors", return_value=[]):
            window = MainWindow()
            worker = CaptureThread(DEFAULT, [1])
            overlay = self.overlay()
            window.worker = worker
            window.overlays[1] = overlay
            worker.result.connect(window._capture_result)
            batch = CaptureBatch([(1, [Box(10, 10, 50, 50, .9, 1)], [], (400, 200), 1)],
                                 1, 50, DEFAULT, ScanTiming(50, 5))
            worker.publish(batch)
            self.assertTrue(overlay.boxes)
            window._changed(categories=[])
            self.assertFalse(overlay.boxes)
            worker.publish(batch)
            self.assertFalse(overlay.boxes)
            window.worker = None
            window.overlays.clear()
            window.close()

    def test_late_callbacks_without_a_worker_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"APPDATA": directory}), patch.object(MainWindow, "_monitors", return_value=[]):
            window = MainWindow()
            status = window.status
            window._capture_result()
            window._capture_failed("late failure")
            window._worker_finished()
            self.assertEqual(window.status, status)
            window.close()

    def test_tracking_crosses_spatial_cell_boundaries_without_losing_associations(self):
        tracker = MotionTracker()
        old = [Box(126, 20, 166, 60, .9, 1), Box(254, 120, 294, 160, .9, 3)]
        new = [Box(258, 120, 298, 160, .9, 3), Box(130, 20, 170, 60, .9, 1)]
        tracker.update(old, ["a", "b"], 1, 1, (800, 300), .3)
        tracker.update(new, ["B", "A"], 1.1, 1.1, (800, 300), .3)
        boxes, patches = tracker.render(1.2, (800, 300), .3)
        self.assertEqual([box.left for box in boxes], [134, 262])
        self.assertEqual(patches, ["A", "B"])


if __name__ == "__main__":
    unittest.main()
