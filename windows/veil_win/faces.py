"""YuNet face detection on ONNX Runtime, with variable-resolution BGR inputs.

Decode follows OpenCV 4.10 FaceDetectorYN's published cls/obj/bbox equations.
No face recognition, identity storage or gender classification is performed.
"""
from pathlib import Path
import sys

import numpy as np
from PIL import Image

from .core import Box, cover, suppress


def face_model_path():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    path = base / "windows" / "assets" / "yunet.onnx"
    if not path.exists():
        raise FileNotFoundError("Face model missing. Run python windows/fetch_face_model.py from the repository root.")
    return path


def decode_faces(outputs, width, height, input_width, scaled_width, scaled_height, threshold):
    sx, sy = width/scaled_width, height/scaled_height
    boxes = []
    for stride in (8, 16, 32):
        cls = outputs[f"cls_{stride}"].reshape(-1)
        obj = outputs[f"obj_{stride}"].reshape(-1)
        scores = np.sqrt(np.clip(cls, 0, 1)*np.clip(obj, 0, 1))
        indices = np.flatnonzero(np.isfinite(scores) & (scores >= threshold))
        rows = outputs[f"bbox_{stride}"].reshape(-1, 4)[indices]
        cols = input_width//stride
        for index, row in zip(indices, rows):
            if not np.isfinite(row).all():
                continue
            cx = (index % cols + row[0])*stride*sx
            cy = (index // cols + row[1])*stride*sy
            w, h = np.exp(np.clip(row[2:4], -10, 10))*stride*np.array([sx, sy])
            left, top = max(0, round(cx-w/2)), max(0, round(cy-h/2))
            right, bottom = min(width, round(cx+w/2)), min(height, round(cy+h/2))
            if right > left and bottom > top:
                boxes.append(Box(left, top, right, bottom, float(scores[index]), 1))
    return suppress(boxes)


class FaceDetector:
    def __init__(self):
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(face_model_path()), options, providers=["CPUExecutionProvider"])
        model_input = self.session.get_inputs()[0]
        if (model_input.shape[:2] != [1, 3] or len(model_input.shape) != 4
                or any(isinstance(dim, int) for dim in model_input.shape[2:])):
            raise ValueError(f"Unexpected YuNet input: {model_input.shape}")
        self.input_name = model_input.name
        self.names = [output.name for output in self.session.get_outputs()]
        needed = {f"{kind}_{stride}" for kind in ("cls", "obj", "bbox") for stride in (8, 16, 32)}
        if not needed.issubset(self.names):
            raise ValueError("Unexpected YuNet outputs")

    def _detect(self, image, threshold, max_edge=2560):
        width, height = image.size
        scale = min(1, max_edge/max(width, height))
        rgb = image if image.mode == "RGB" else image.convert("RGB")
        scaled = rgb if scale == 1 else rgb.resize((max(1, round(width*scale)), max(1, round(height*scale))), Image.Resampling.BILINEAR)
        input_width, input_height = (int(np.ceil(dim/32))*32 for dim in scaled.size)
        # Fill contiguous NCHW directly, without a second full float32 frame.
        data = np.zeros((1, 3, input_height, input_width), dtype=np.float32)
        data[0, :, :scaled.height, :scaled.width] = np.asarray(scaled)[:, :, ::-1].transpose(2, 0, 1)
        outputs = dict(zip(self.names, self.session.run(None, {self.input_name: data})))
        return decode_faces(outputs, width, height, input_width, scaled.width, scaled.height, threshold)

    def detect(self, image, settings, *, tiled=False, cancelled=None):
        # Preserve native detail up to 2560px, avoiding many fixed square scans.
        if cancelled is not None and cancelled():
            return []
        boxes = self._detect(image, settings["confidence"]/100)
        return cover(boxes, *image.size, settings["coverage"])
