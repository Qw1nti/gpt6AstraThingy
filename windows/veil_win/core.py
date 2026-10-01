"""Local NudeNet inference and image rendering shared by live capture and export."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


LABELS = (
    "Covered genitals (female)", "Face (female)", "Exposed buttocks",
    "Exposed breasts (female)", "Exposed genitals (female)", "Exposed chest (male)",
    "Exposed anus", "Exposed feet", "Covered belly", "Covered feet",
    "Covered armpits", "Exposed armpits", "Face (male)", "Exposed belly",
    "Exposed genitals (male)", "Covered anus", "Covered breasts (female)",
    "Covered buttocks",
)
DEFAULT_CATEGORIES = (2, 3, 4, 6, 14)
GROUPS = {
    "NSFW — EXPOSED": (4, 14, 3, 2, 6),
    "NSFW — COVERED (OPTIONAL)": (0, 16, 17, 15),
    "FACES": (1, 12),
    "BODY PARTS": (13, 8, 5, 7, 9, 11, 10),
}


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    right: int
    bottom: int
    score: float
    category: int


def overlap(a: Box, b: Box) -> float:
    area = max(0, min(a.right, b.right) - max(a.left, b.left)) * max(0, min(a.bottom, b.bottom) - max(a.top, b.top))
    union = (a.right-a.left)*(a.bottom-a.top) + (b.right-b.left)*(b.bottom-b.top) - area
    return area / union if union else 0.0


def suppress(boxes: Sequence[Box]) -> list[Box]:
    kept: list[Box] = []
    for box in sorted(boxes, key=lambda item: item.score, reverse=True):
        if not any(box.category == prior.category and overlap(box, prior) > .45 for prior in kept):
            kept.append(box)
    return kept


def cover(boxes: Sequence[Box], width: int, height: int, coverage: int) -> list[Box]:
    margin = max(-40, min(70, coverage)) / 100.0
    result = []
    for box in boxes:
        dx, dy = (box.right-box.left)*margin, (box.bottom-box.top)*margin
        left, top = max(0, round(box.left-dx)), max(0, round(box.top-dy))
        right, bottom = min(width, round(box.right+dx)), min(height, round(box.bottom+dy))
        if right > left and bottom > top:
            result.append(Box(left, top, right, bottom, box.score, box.category))
    return result


def scan_regions(width: int, height: int, edge: int = 1280) -> list[tuple[int, int, int, int]]:
    """Whole display plus overlapping crops, preserving detail on large desktops."""
    def starts(length):
        if length <= edge:
            return [0]
        # At least 25% overlap, with the last crop flush against the display edge.
        count = int(np.ceil((length-edge)/(edge*.75)))
        return [round(i*(length-edge)/count) for i in range(count+1)]
    whole = (0, 0, width, height)
    crops = [(x, y, min(width, x+edge), min(height, y+edge))
             for y in starts(height) for x in starts(width)]
    return [whole] + [crop for crop in crops if crop != whole]


def decode(output: np.ndarray, width: int, height: int, threshold: float,
           categories: Sequence[int], coverage: int) -> list[Box]:
    """NudeNet 320n: [1,22,N] or [1,N,22], right/bottom square padding."""
    output = np.asarray(output)
    if output.ndim != 3 or output.shape[0] != 1:
        raise ValueError(f"Unexpected model output shape: {output.shape}")
    rows = output[0].T if output.shape[1] == 22 else output[0]
    if rows.shape[1] != 22 or width < 1 or height < 1:
        raise ValueError(f"Unexpected model output shape: {output.shape}")
    selected = set(categories)
    scale = max(width, height) / 320.0
    boxes: list[Box] = []
    # Filter the thousands of empty YOLO candidates in NumPy before Python NMS.
    class_ids = np.argmax(rows[:, 4:], axis=1)
    scores = rows[np.arange(len(rows)), 4+class_ids]
    valid = np.isin(class_ids, list(selected)) & np.isfinite(scores) & (scores >= threshold)
    for row, category in zip(rows[valid], class_ids[valid]):
        category = int(category)
        score = float(row[4 + category])
        if category not in selected or not np.isfinite(score) or score < threshold:
            continue
        cx, cy, w, h = (float(x) * scale for x in row[:4])
        if not all(np.isfinite(x) for x in (cx, cy, w, h)) or w <= 0 or h <= 0:
            continue
        dx, dy = w * .5, h * .5
        left, top = max(0, round(cx-dx)), max(0, round(cy-dy))
        right, bottom = min(width, round(cx+dx)), min(height, round(cy+dy))
        if right > left and bottom > top:
            boxes.append(Box(left, top, right, bottom, score, category))
    # Coverage must not change which overlapping detections survive NMS.
    return cover(suppress(boxes), width, height, coverage)


def model_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    path = base / "app" / "src" / "main" / "assets" / "320n.onnx"
    if not path.exists():
        raise FileNotFoundError("Detector model missing. Run python scripts/fetch_model.py from the repository root.")
    return path


class Detector:
    def __init__(self):
        self.session = None
        self.face_detector = None

    def _load_body_model(self):
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(model_path()), options, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        shape = self.session.get_inputs()[0].shape
        if len(shape) != 4 or any(isinstance(actual, int) and actual != expected
                                  for actual, expected in zip(shape, (1, 3, 320, 320))):
            raise ValueError(f"Unexpected detector input: {shape}")

    def detect(self, image: Image.Image, settings: dict, *, tiled: bool = False, cancelled=None) -> list[Box]:
        selected = set(settings["categories"])
        boxes = []
        if selected.intersection((1, 12)):
            if self.face_detector is None:
                from .faces import FaceDetector
                self.face_detector = FaceDetector()
            boxes.extend(self.face_detector.detect(image, settings, tiled=tiled, cancelled=cancelled))
        body_categories = sorted(selected.difference((1, 12)))
        if body_categories and (cancelled is None or not cancelled()):
            if self.session is None:
                self._load_body_model()
            boxes.extend(self._detect_body(image, {**settings, "categories": body_categories}, tiled=tiled, cancelled=cancelled))
        return boxes

    def _detect_body(self, image: Image.Image, settings: dict, *, tiled=False, cancelled=None) -> list[Box]:
        if tiled:
            boxes = []
            for left, top, right, bottom in scan_regions(*image.size):
                if cancelled is not None and cancelled():
                    return []
                part = image if (left, top, right, bottom) == (0, 0, *image.size) else image.crop((left, top, right, bottom))
                for box in self._detect_body(part, {**settings, "coverage": 0}):
                    boxes.append(Box(box.left+left, box.top+top, box.right+left,
                                     box.bottom+top, box.score, box.category))
            return cover(suppress(boxes), *image.size, settings["coverage"])
        width, height = image.size
        edge = max(width, height)
        scaled = image.convert("RGB").resize((max(1, round(width*320/edge)), max(1, round(height*320/edge))), Image.Resampling.BILINEAR)
        square = Image.new("RGB", (320, 320))
        square.paste(scaled, (0, 0))
        data = np.asarray(square, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
        output = self.session.run(None, {self.input_name: np.ascontiguousarray(data)})[0]
        return decode(output, width, height, settings["confidence"] / 100,
                      settings["categories"], settings["coverage"])


def censor_image(source: Image.Image, boxes: Sequence[Box], settings: dict,
                 custom_image: Image.Image | None = None) -> Image.Image:
    """Render a saveable RGB copy. Outline mode deliberately leaves pixels visible."""
    output = source.convert("RGB").copy()
    draw = ImageDraw.Draw(output)
    rects = [(b.left, b.top, b.right, b.bottom) for b in boxes]
    if settings.get("inverse") and settings["style"] != "Outline":
        # Keep detections visible while concealing everything else.
        covered = Image.new("RGB", output.size, settings["color"])
        for rect in rects:
            covered.paste(output.crop(rect), rect[:2])
        return covered
    style = settings["style"]
    for box, rect in zip(boxes, rects):
        x1, y1, x2, y2 = rect
        if style == "Outline":
            draw.rectangle((x1, y1, x2-1, y2-1), outline=settings["border_color"], width=3)
            continue
        if style in ("Mosaic", "Pixelated Blur"):
            part = output.crop(rect)
            block = max(4, int(settings["pixel_size"]))
            small = part.resize((max(1, part.width//block), max(1, part.height//block)), Image.Resampling.BOX)
            output.paste(small.resize(part.size, Image.Resampling.NEAREST), rect[:2])
        elif style == "Blur":
            output.paste(output.crop(rect).filter(ImageFilter.GaussianBlur(radius=18)), rect[:2])
        elif style == "Custom image" and custom_image is not None:
            output.paste(custom_image.convert("RGB").resize((x2-x1, y2-y1), Image.Resampling.LANCZOS), rect[:2])
        else:
            ImageDraw.Draw(output).rectangle((x1, y1, x2-1, y2-1), fill=settings["color"])
        draw = ImageDraw.Draw(output)
        if style in ("Mosaic", "Pixelated Blur"):
            draw.rectangle((x1, y1, x2-1, y2-1), outline=settings["border_color"], width=3)
        if style == "Labeled":
            draw.text((x1+8, y1+8), settings["label"][:32], fill="#ffffff", font=ImageFont.load_default())
    return output
