"""Run with QT_QPA_PLATFORM=offscreen on CI to catch view construction errors."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="veil-ui-")

from PySide6.QtWidgets import QApplication
from veil_win.app import MainWindow

app = QApplication([])
window = MainWindow()
for page in ("Home", "Body Parts", "Censor Styles", "Export", "Settings", "Help"):
    window.show_page(page)
    assert window.page_name == page
window.close()
app.quit()
print("All six Windows views constructed successfully.")
