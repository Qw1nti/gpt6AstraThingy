"""Execute the exact shipped model once on the Windows build runner."""
from PIL import Image
from pathlib import Path
from veil_win.core import Detector
from veil_win.settings import DEFAULT

detector = Detector()
boxes = detector.detect(Image.new("RGB", (640, 360), "#888888"), DEFAULT)
assert isinstance(boxes, list)
print(f"ONNX inference succeeded; {len(boxes)} synthetic detections")

with Image.open(Path(__file__).parent / "fixtures" / "astronaut.jpg") as file:
    portrait = file.convert("RGB")
settings = {**DEFAULT, "categories": [1, 12]}
assert detector.detect(portrait, settings), "Real portrait recognition failed"
desktop = Image.new("RGB", (1920, 1080), "#888888")
desktop.paste(portrait, (700, 200))
boxes = detector.detect(desktop, settings, tiled=True)
assert any(b.left < 920 < b.right and b.top < 320 < b.bottom for b in boxes), boxes
assert len(boxes) == 1, f"Overlapping crops produced duplicate face masks: {boxes}"
print("Real face recognition passed at portrait and desktop sizes.")
