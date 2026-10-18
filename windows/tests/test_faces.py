import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from veil_win.core import Detector
from veil_win.faces import decode_faces, FaceDetector
from veil_win.settings import DEFAULT, migrate_settings


def empty_heads(width, height):
    heads = {}
    for stride in (8, 16, 32):
        count = width//stride*(height//stride)
        heads[f"cls_{stride}"] = np.zeros((1, count, 1), np.float32)
        heads[f"obj_{stride}"] = np.zeros((1, count, 1), np.float32)
        heads[f"bbox_{stride}"] = np.zeros((1, count, 4), np.float32)
    return heads


class FaceTests(unittest.TestCase):
    def test_rectangular_decode_remaps_scale_padding_and_filters_scores(self):
        heads = empty_heads(64, 32)
        heads["cls_8"][0, 11, 0] = .81
        heads["obj_8"][0, 11, 0] = 1
        heads["bbox_8"][0, 11] = [.5, .5, np.log(2), np.log(2)]
        heads["cls_8"][0, 12, 0] = np.nan
        boxes = decode_faces(heads, 100, 40, 64, 50, 20, .5)
        self.assertEqual(len(boxes), 1)
        self.assertEqual((boxes[0].left, boxes[0].top, boxes[0].right, boxes[0].bottom), (40, 8, 72, 40))

    def test_preprocessing_uses_bgr_raw_values_and_rectangular_padding(self):
        detector = FaceDetector.__new__(FaceDetector)
        detector.input_name = "input"
        heads = empty_heads(64, 32)
        detector.names = list(heads)

        class Session:
            def run(self, _, inputs):
                data = inputs["input"]
                self_test.assertEqual(data.shape, (1, 3, 32, 64))
                self_test.assertEqual(data.dtype, np.float32)
                self_test.assertTrue(data.flags.c_contiguous)
                np.testing.assert_array_equal(data[0, :, 0, 0], [30, 20, 10])
                self_test.assertFalse(data[:, :, 20:, :].any())
                self_test.assertFalse(data[:, :, :, 50:].any())
                return list(heads.values())

        self_test = self
        detector.session = Session()
        self.assertEqual(detector._detect(Image.new("RGB", (50, 20), (10, 20, 30)), .45), [])

    def test_face_only_and_empty_categories_skip_body_inference(self):
        detector = Detector()
        with patch("veil_win.faces.FaceDetector") as model, patch.object(detector, "_load_body_model") as body:
            model.return_value.detect.return_value = []
            image = Image.new("RGB", (64, 64))
            detector.detect(image, {**DEFAULT, "categories": []})
            model.assert_not_called()
            detector.detect(image, {**DEFAULT, "categories": [12]})
            model.return_value.detect.assert_called_once()
            body.assert_not_called()

    def test_legacy_face_selection_becomes_all_faces_and_preserves_body_filters(self):
        for categories in ([1, 3], [3, 12]):
            settings = migrate_settings({"categories": categories, "confidence": 30})
            self.assertEqual(settings["categories"], [1, 3, 12])
            self.assertEqual(settings["confidence"], 30)
            self.assertTrue(settings["motion_prediction"])
        self.assertEqual(migrate_settings({"categories": [3]})["categories"], [3])


if __name__ == "__main__":
    unittest.main()
