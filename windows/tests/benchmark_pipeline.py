"""Synthetic pipeline microbenchmarks, not an owner-PC FPS or accuracy test.

Run with PYTHONPATH=windows. Compare the same script/environment on two code
revisions; timings include warm-up and report median work over eight passes.
No screen contents or model inference are used.
"""
import json
from statistics import median
from time import perf_counter

import numpy as np
from PIL import Image

from veil_win.capture import qimage
from veil_win.core import Box, censor_image
from veil_win.settings import DEFAULT
from veil_win.tracking import MotionTracker

try:
    from veil_win.effects import PatchRenderer
except ImportError:  # Supports measuring the prior revision with this script.
    PatchRenderer = None


def measure(callback):
    callback()
    values = []
    for _ in range(8):
        started = perf_counter()
        callback()
        values.append((perf_counter()-started)*1000)
    return round(median(values), 3)


frame = Image.fromarray(np.random.default_rng(5).integers(0, 256, (2160, 3840, 3), dtype=np.uint8))
boxes = [Box(x, y, x+320, y+240, .9, 1) for y in range(0, 1920, 320) for x in range(0, 3520, 400)]
custom = Image.new("RGB", (512, 512), "blue")
result = {}
for style in ("Blur", "Pixelated Blur", "Custom image"):
    settings = {**DEFAULT, "style": style}
    renderer = PatchRenderer() if PatchRenderer else None

    def effects():
        if renderer:
            renderer.render(frame, boxes, settings, custom)
        else:
            for box in boxes:
                part = frame.crop((box.left, box.top, box.right, box.bottom))
                qimage(censor_image(part, [Box(0, 0, part.width, part.height, .9, 1)], settings, custom))

    result[f"{style}: 54 patches ms"] = measure(effects)

def tracking():
    tracker = MotionTracker()
    boxes = [Box(20+col*180, 20+row*100, 60+col*180, 60+row*100, .9, 1)
             for row in range(15) for col in range(20)]
    tracker.update(boxes, [], 1, 1, (3840, 2160), .3)
    moved = [Box(b.left+5, b.top, b.right+5, b.bottom, b.score, b.category) for b in boxes]
    tracker.update(moved, [], 1.1, 1.1, (3840, 2160), .3)
    assert len(tracker.render(1.15, (3840, 2160), .3)[0]) == 300
    assert all(track.hits == 2 for track in tracker.tracks)

result["300-track association ms"] = measure(tracking)
print(json.dumps(result, indent=2))
