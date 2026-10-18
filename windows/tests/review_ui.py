"""Render all redesigned views using Qt for visual review, never screen capture."""
import argparse
import os
from pathlib import Path
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="veil-review-")

from PySide6.QtWidgets import QApplication
from veil_win.app import MainWindow, PAGES
from veil_win.settings import STYLES


parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
parser.add_argument("--native", action="store_true", help="Use the Windows desktop plugin on the Windows runner")
args = parser.parse_args()
if args.native:
    os.environ.pop("QT_QPA_PLATFORM", None)
destination = Path(args.output)
destination.mkdir(parents=True, exist_ok=True)
app = QApplication([])
window = MainWindow()
window.show()
for theme in ("Light", "Dark"):
    window._appearance(theme)
    for width, height in ((1120, 780), (820, 600)):
        window.resize(width, height)
        for page, (label, _, _) in PAGES.items():
            window.show_page(page)
            app.processEvents()
            app.processEvents()
            assert window.scroll.horizontalScrollBar().maximum() == 0, (theme, width, page)
            window.grab().save(str(destination/f"{theme}-{width}-{label}.png"))
    window.resize(1120, 780)
    for style in STYLES:
        window._style(style)
        app.processEvents()
        app.processEvents()
        # Show the contextual options below the preview.
        window.scroll.verticalScrollBar().setValue(window.scroll.verticalScrollBar().maximum())
        app.processEvents()
        window.grab().save(str(destination/f"{theme}-effect-{style.replace(' ', '-')}.png"))
window.close()
app.quit()
print("Rendered all six views in both modes and sizes, plus all style controls.")
