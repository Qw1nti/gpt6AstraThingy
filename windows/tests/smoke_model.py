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
settings = {**DEFAULT, "categories": [1, 12], "coverage": 0}
faces_only = Detector()
assert faces_only.detect(portrait, settings), "Real portrait recognition failed"
assert faces_only.session is None, "Face-only filtering loaded the body model"
assert not faces_only.detect(Image.new("RGB", (1920, 1080), "#888888"), settings), "Blank screen produced face detections"
desktop = Image.new("RGB", (1920, 1080), "#888888")
desktop.paste(portrait, (700, 200))
boxes = faces_only.detect(desktop, settings, tiled=True)
assert any(b.left < 920 < b.right and b.top < 320 < b.bottom for b in boxes), boxes
assert len(boxes) == 1, f"Duplicate face masks: {boxes}"
for edge in (128, 80, 64):
    desktop = Image.new("RGB", (1920, 1080), "#888888")
    desktop.paste(portrait.resize((edge, edge)), (800, 400))
    boxes = faces_only.detect(desktop, settings, tiled=True)
    x, y = 800+220*edge/512, 400+120*edge/512
    assert len(boxes) == 1 and boxes[0].left < x < boxes[0].right and boxes[0].top < y < boxes[0].bottom, (edge, boxes)
    print(f"Small-face fixture passed: portrait {edge}px, face box {boxes[0].right-boxes[0].left}px")
desktop = Image.new("RGB", (1920, 1080), "#888888")
centers = []
for row in range(4):
    for col in range(9):
        x, y = 50+col*190, 80+row*220
        desktop.paste(portrait.resize((80, 80)), (x, y))
        centers.append((x+220*80/512, y+120*80/512))
boxes = faces_only.detect(desktop, settings, tiled=True)
assert len(boxes) == len(centers), (len(boxes), len(centers))
assert all(any(b.left < x < b.right and b.top < y < b.bottom for b in boxes) for x, y in centers), boxes
print("Both local models, blank-screen rejection, small faces and 36-face desktop fixture passed.")
