import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from veil_win.core import Box, decode, censor_image
from veil_win.settings import DEFAULT, SettingsStore


class CoreTests(unittest.TestCase):
    def test_decode_padding_and_categories(self):
        raw = np.zeros((1, 22, 2), dtype=np.float32)
        raw[0, :4, 0] = [160, 80, 80, 40]
        raw[0, 4 + 3, 0] = .92
        raw[0, :4, 1] = [160, 80, 80, 40]
        raw[0, 4 + 6, 1] = .85
        result = decode(raw, 640, 320, .45, [3], 0)
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0].left, result[0].top, result[0].right, result[0].bottom), (240, 120, 400, 200))
        small = decode(raw, 640, 320, .45, [3], -40)
        self.assertEqual(small[0].right-small[0].left, 32)

    def test_dense_boxes_are_not_truncated(self):
        raw = np.zeros((1, 22, 50), dtype=np.float32)
        for i in range(50):
            raw[0, :4, i] = [8+i*6, 16, 3, 3]
            raw[0, 7, i] = .8
        self.assertEqual(len(decode(raw, 640, 320, .45, [3], 0)), 50)

    def test_render_outline_leaves_center_visible(self):
        source = Image.new("RGB", (40, 40), "#77aa22")
        box = Box(5, 5, 30, 30, .9, 3)
        settings = {**DEFAULT, "style": "Outline"}
        output = censor_image(source, [box], settings)
        self.assertEqual(output.getpixel((15, 15)), source.getpixel((15, 15)))
        self.assertNotEqual(output.getpixel((5, 5)), source.getpixel((5, 5)))

    def test_inverse_and_mosaic(self):
        source = Image.new("RGB", (40, 40), "#77aa22")
        box = Box(5, 5, 30, 30, .9, 3)
        inverse = censor_image(source, [box], {**DEFAULT, "inverse": True})
        self.assertEqual(inverse.getpixel((15, 15)), source.getpixel((15, 15)))
        self.assertNotEqual(inverse.getpixel((0, 0)), source.getpixel((0, 0)))
        mosaic = censor_image(source, [box], {**DEFAULT, "style": "Mosaic"})
        self.assertEqual(mosaic.size, source.size)
        inverse_outline = censor_image(source, [box], {**DEFAULT, "style": "Outline", "inverse": True})
        self.assertEqual(inverse_outline.getpixel((0, 0)), source.getpixel((0, 0)))

    def test_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = SettingsStore(path)
            store.update(coverage=-20, categories=[1, 3])
            loaded = SettingsStore(path)
            self.assertEqual(loaded.current["coverage"], -20)
            self.assertEqual(loaded.current["categories"], [1, 3])


if __name__ == "__main__":
    unittest.main()
