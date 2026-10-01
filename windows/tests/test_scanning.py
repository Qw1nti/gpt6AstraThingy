import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
import numpy as np
from veil_win.core import Box, censor_image
from veil_win.scanning import ScanMeter, scan_delay, interval_label
from veil_win.settings import DEFAULT, SettingsStore, migrate_settings


class ScanningTests(unittest.TestCase):
    def test_pacing_subtracts_work_and_never_catches_up(self):
        self.assertAlmostEqual(scan_delay(200, .05), .15)
        self.assertAlmostEqual(scan_delay(50, .12), .005)
        self.assertAlmostEqual(scan_delay(0, .12), .005)

    def test_meter_measures_cycle_rate_instead_of_reciprocal_work(self):
        meter = ScanMeter()
        self.assertIsNone(meter.observe(1, 1.05).scans_per_second)
        timing = meter.observe(1.2, 1.25)
        self.assertAlmostEqual(timing.work_ms, 50)
        self.assertAlmostEqual(timing.scans_per_second, 5)
        # A slow scan reduces achieved rate regardless of the requested interval.
        meter.observe(1.4, 1.7)
        timing = meter.observe(1.705, 1.805)
        self.assertLess(timing.scans_per_second, 5)

    def test_old_profiles_migrate_rate_and_pixel_style_without_losing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"settings.json"
            path.write_text(json.dumps({"active": "Custom", "profiles": {"Custom": {
                "preset": "High", "style": "Mosaic", "pixel_size": 38,
                "border_color": "#ffffff", "coverage": -20}}}))
            store = SettingsStore(path)
            self.assertEqual(store.current["scan_interval_ms"], 66)
            self.assertEqual(store.current["style"], "Pixelated Blur")
            self.assertEqual(store.current["pixel_size"], 38)
            self.assertEqual(store.current["border_color"], "#ffffff")
            self.assertEqual(store.current["coverage"], -20)
            store.save()
            self.assertEqual(SettingsStore(path).current, store.current)

    def test_rate_bounds_and_legacy_fastest(self):
        self.assertEqual(migrate_settings({"preset": "Ultra"})["scan_interval_ms"], 0)
        self.assertEqual(migrate_settings({"scan_interval_ms": -1})["scan_interval_ms"], 0)
        self.assertEqual(migrate_settings({"scan_interval_ms": 9000})["scan_interval_ms"], 1000)
        self.assertEqual(migrate_settings({"scan_interval_ms": "bad"})["scan_interval_ms"], 150)
        self.assertIn("Fastest", interval_label(0))

    def test_pixelated_blur_reduces_detail_and_keeps_border(self):
        pixels = np.random.default_rng(4).integers(0, 256, (80, 80, 3), dtype=np.uint8)
        source = Image.fromarray(pixels)
        box = Box(10, 10, 70, 70, 1, 1)
        settings = {**DEFAULT, "style": "Pixelated Blur", "pixel_size": 20}
        output = censor_image(source, [box], settings)
        self.assertEqual(output.getpixel((20, 20)), output.getpixel((25, 25)))
        self.assertNotEqual(source.getpixel((20, 20)), output.getpixel((20, 20)))
        self.assertEqual(output.getpixel((10, 10)), (255, 69, 69))
        self.assertEqual(output.getpixel((0, 0)), source.getpixel((0, 0)))
        self.assertEqual(output.tobytes(), censor_image(source, [box], {**settings, "style": "Mosaic"}).tobytes())
