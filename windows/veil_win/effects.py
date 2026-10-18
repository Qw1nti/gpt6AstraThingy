"""Render only live mask pixels, with bounded reuse of private custom masks."""
from collections import OrderedDict

from PIL import Image, ImageDraw, ImageFilter
from PySide6.QtGui import QImage


def qimage(image):
    rgb = image if image.mode == "RGB" else image.convert("RGB")
    # Own the bytes before crossing threads; never depend on a PIL buffer lifetime.
    return QImage(rgb.tobytes(), rgb.width, rgb.height, rgb.width*3, QImage.Format.Format_RGB888).copy()


class PatchRenderer:
    def __init__(self, limit_bytes=8*1024*1024):
        self.limit_bytes = limit_bytes
        self.cache = OrderedDict()
        self.cache_bytes = 0
        self.custom = None

    def render(self, frame, boxes, settings, custom=None):
        if custom is not self.custom:
            self.cache.clear()
            self.cache_bytes = 0
            self.custom = custom
        style = settings["style"]
        if settings["inverse"] or style not in ("Mosaic", "Pixelated Blur", "Blur", "Custom image"):
            return []
        patches = []
        for box in boxes:
            rect = (box.left, box.top, box.right, box.bottom)
            size = (box.right-box.left, box.bottom-box.top)
            if style == "Custom image" and custom is not None:
                if size in self.cache:
                    patch = self.cache.pop(size)
                    self.cache[size] = patch
                else:
                    patch = qimage(custom.resize(size, Image.Resampling.LANCZOS))
                    cost = patch.sizeInBytes()
                    if cost <= self.limit_bytes:
                        while self.cache and self.cache_bytes+cost > self.limit_bytes:
                            _, old = self.cache.popitem(last=False)
                            self.cache_bytes -= old.sizeInBytes()
                        self.cache[size] = patch
                        self.cache_bytes += cost
                patches.append(patch)
                continue
            if style == "Custom image":
                patches.append(None)  # Overlay supplies the configured solid fallback.
                continue
            part = frame.crop(rect)
            if style == "Blur":
                part = part.filter(ImageFilter.GaussianBlur(radius=18))
            else:
                block = max(4, int(settings["pixel_size"]))
                part = part.resize((max(1, size[0]//block), max(1, size[1]//block)), Image.Resampling.BOX).resize(size, Image.Resampling.NEAREST)
                ImageDraw.Draw(part).rectangle((0, 0, size[0]-1, size[1]-1), outline=settings["border_color"], width=3)
            patches.append(qimage(part))
        return patches
