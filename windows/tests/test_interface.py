"""UI workflows that must keep their state across the Fluent redesign."""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QSlider, QSpinBox

from veil_win.app import MainWindow, PAGES, PhotoJob
from veil_win.capture import CaptureThread
from veil_win.settings import DEFAULT, SettingsStore, STYLES
from veil_win.ui import CheckBox, ToggleSwitch

APP = QApplication.instance() or QApplication([])


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"APPDATA": self.directory.name})
        self.env.start()
        self.monitors = patch.object(MainWindow, "_monitors", return_value=[])
        self.monitors.start()
        self.window = MainWindow()
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        self.window.worker = None  # Fake workers in these tests are never started.
        self.window.close()
        APP.processEvents()
        self.monitors.stop()
        self.env.stop()
        self.directory.cleanup()

    def test_theme_is_global_persistent_and_does_not_restart_capture(self):
        window = self.window
        window.show_page("Settings")
        current_page = window.scroll.widget()
        worker = CaptureThread(window.store.current, [1])
        window.worker = worker
        original = dict(worker.settings)
        window._appearance("Dark")
        self.assertTrue(window.dark)
        window._appearance("Light")
        self.assertFalse(window.dark)
        self.assertIs(window.scroll.widget(), current_page)
        self.assertIs(window.worker, worker)
        self.assertEqual(worker.settings, original)
        loaded = SettingsStore(window.store.path)
        self.assertEqual(loaded.appearance, "Light")
        loaded.profiles["Other"] = dict(DEFAULT)
        loaded.active = "Other"
        loaded.save()
        self.assertEqual(SettingsStore(loaded.path).appearance, "Light")

    def test_legacy_preferences_keep_categories_style_and_default_to_system_theme(self):
        path = Path(self.directory.name)/"old.json"
        path.write_text(json.dumps({"active": "Custom", "profiles": {
            "Custom": {**DEFAULT, "categories": [1, 3, 12], "style": "Pixelated Blur", "pixel_size": 28}}}))
        store = SettingsStore(path)
        self.assertEqual(store.appearance, "System")
        self.assertEqual(store.current["categories"], [1, 3, 12])
        self.assertEqual(store.current["pixel_size"], 28)
        self.assertEqual(store.current["style"], "Pixelated Blur")

    def test_navigation_retains_shell_and_running_session(self):
        window = self.window
        shell = window.centralWidget()
        worker = CaptureThread(DEFAULT, [1])
        window.worker = worker
        for key, (label, _, _) in PAGES.items():
            window.nav_buttons[key].click()
            APP.processEvents()
            self.assertEqual(window.page_name, key)
            self.assertIs(window.centralWidget(), shell)
            self.assertIs(window.worker, worker)
            self.assertEqual(sum(control.isChecked() for control in window.nav_buttons.values()), 1)
            self.assertEqual(window.nav_buttons[key].accessibleName(), label)
        window.resize(820, 600)
        APP.processEvents()
        self.assertEqual(window.sidebar.width(), 72)
        self.assertTrue(all(not button.text() and not button.icon().isNull()
                            for button in window.nav_buttons.values()))

    def test_pages_fit_without_horizontal_scrolling_in_both_modes(self):
        window = self.window
        for mode in ("Light", "Dark"):
            window._appearance(mode)
            for size in ((820, 600), (1120, 780)):
                window.resize(*size)
                for page in PAGES:
                    window.show_page(page)
                    APP.processEvents()
                    self.assertEqual(window.scroll.horizontalScrollBar().maximum(), 0, (mode, size, page))

    def test_keyboard_controls_change_detection_and_prediction(self):
        window = self.window
        window.show_page("Detection")
        faces = next(c for c in window.scroll.widget().findChildren(CheckBox) if c.text() == "Detect faces")
        faces.setFocus()
        QTest.keyClick(faces, Qt.Key.Key_Space)
        self.assertTrue(set((1, 12)).issubset(window.store.current["categories"]))
        self.assertIn("6 detection", window.category_summary.text())
        window.show_page("Settings")
        prediction = window.scroll.widget().findChild(ToggleSwitch)
        prediction.setFocus()
        QTest.keyClick(prediction, Qt.Key.Key_Space)
        self.assertFalse(window.store.current["motion_prediction"])

    def test_style_switches_preserve_values_and_contextual_controls(self):
        window = self.window
        window.store.update(pixel_size=28, label="PRIVATE", coverage=-12, border_color="#a0ed5b")
        for style in STYLES:
            window._style(style)
            APP.processEvents()
            body = window.scroll.widget()
            self.assertEqual(sum(tile.isChecked() for tile in window.style_buttons.values()), 1)
            self.assertEqual(bool(body.findChildren(QSpinBox)), style == "Pixelated Blur")
            self.assertEqual(any(field.accessibleName() == "Censor text" for field in body.findChildren(QLineEdit)),
                             style == "Labeled")
            self.assertEqual(window.store.current["coverage"], -12)
        self.assertEqual(window.store.current["pixel_size"], 28)
        self.assertEqual(window.store.current["label"], "PRIVATE")
        self.assertEqual(window.store.current["border_color"], "#a0ed5b")
        window._style("Outline")
        self.assertTrue(any("does not hide" in label.text() for label in window.scroll.widget().findChildren(QLabel)))

    def test_photo_work_and_outline_status_survive_navigation(self):
        window = self.window
        window.show_page("Photos")
        window.photo_job = PhotoJob("", {**DEFAULT, "style": "Outline"})
        window._photo_ready(Image.new("RGB", (80, 60), "blue"), 1)
        photo = window.photo
        window.show_page("Appearance")
        window._style("Blur")
        window.show_page("Photos")
        self.assertIs(window.photo, photo)
        self.assertIn("Outline only", window.export_status.text())
        self.assertTrue(window.save_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
