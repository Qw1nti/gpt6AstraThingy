"""Execute the exact shipped model once on the Windows build runner."""
from PIL import Image
from veil_win.core import Detector
from veil_win.settings import DEFAULT

boxes = Detector().detect(Image.new("RGB", (640, 360), "#888888"), DEFAULT)
assert isinstance(boxes, list)
print(f"ONNX inference succeeded; {len(boxes)} synthetic detections")
