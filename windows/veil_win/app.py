"""Independent Windows desktop interface for Veil."""
from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QComboBox, QSlider, QCheckBox, QLineEdit,
    QFileDialog, QMessageBox, QGridLayout, QSpinBox)

from .capture import CaptureThread, Overlay, qimage
from .core import Box, Detector, GROUPS, LABELS, censor_image
from .settings import SettingsStore, STYLES
from .displays import display_devices, match_screens
from .diagnostics import configure_logging
from .scanning import interval_label

LOG = logging.getLogger(__name__)

RED = "#e53935"
BG = "#090909"
CARD = "#151515"
DIM = "#a7a7a7"
CSS = """
QMainWindow, QWidget#root, QScrollArea, QWidget#page {background:#090909;color:#f5f5f5}
QWidget {font-family:'Segoe UI';font-size:13px;color:#f5f5f5}
QFrame#card {background:#151515;border:1px solid #303030;border-radius:14px}
QFrame#preview {background:#0b0b0b;border:1px solid #303030;border-radius:5px}
QLabel#muted {color:#a7a7a7;font-size:12px}
QLabel#eyebrow {color:#b9b9b9;font-size:11px;font-weight:700;letter-spacing:2px}
QLabel#headline {font-size:20px;font-weight:700}
QPushButton {background:#222;border:1px solid #383838;border-radius:8px;padding:10px 16px;min-height:19px}
QPushButton:hover {border-color:#e53935;background:#2b1b1b}
QPushButton:checked, QPushButton#primary {background:#e53935;border-color:#e53935;color:white;font-weight:700}
QPushButton#primary:hover {background:#f34a46}
QPushButton#nav {background:transparent;border:0;border-radius:7px;text-align:left;padding:12px 16px}
QPushButton#nav:checked {background:#311819;border-left:3px solid #e53935;color:white}
QComboBox,QLineEdit,QSpinBox {background:#191919;border:1px solid #393939;border-radius:7px;padding:8px;min-height:24px}
QComboBox:focus,QLineEdit:focus,QSpinBox:focus {border:1px solid #e53935}
QComboBox QAbstractItemView {background:#191919;selection-background-color:#a22d2d}
QCheckBox {spacing:9px;min-height:28px}
QCheckBox::indicator {width:18px;height:18px;border:1px solid #555;border-radius:4px;background:#050505}
QCheckBox::indicator:checked {background:#e53935;border-color:#e53935}
QSlider::groove:horizontal {height:5px;background:#343434;border-radius:2px}
QSlider::handle:horizontal {width:16px;margin:-6px 0;background:#e53935;border:2px solid white;border-radius:8px}
QScrollBar:vertical {background:#0a0a0a;width:10px}
QScrollBar::handle:vertical {background:#555;border-radius:5px;min-height:30px}
"""


def text(value: str, kind="") -> QLabel:
    label = QLabel(value)
    label.setWordWrap(True)
    if kind:
        label.setObjectName(kind)
    return label


def button(label: str, callback, primary=False, checkable=False) -> QPushButton:
    control = QPushButton(label)
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    control.setCheckable(checkable)
    if primary:
        control.setObjectName("primary")
    control.clicked.connect(callback)
    return control


def card(title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 19, 22, 20)
    layout.setSpacing(14)
    layout.addWidget(text(title, "eyebrow"))
    if subtitle:
        layout.addWidget(text(subtitle, "muted"))
    return frame, layout


class StarHeader(QWidget):
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.setMinimumHeight(136)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#000000"))
        random.seed(19)
        for _ in range(32):
            x, y = random.randrange(max(1, self.width())), random.randrange(8, 127)
            radius = random.choice((1, 2, 3))
            p.setPen(QPen(QColor("#ba1010"), 1))
            p.drawLine(x-radius*2, y, x+radius*2, y)
            p.drawLine(x, y-radius*2, x, y+radius*2)
        size = min(44, max(23, self.width()//24))
        font = QFont("Consolas", size, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        p.setFont(font)
        for offset, shade, width in ((3, "#510000", 7), (1, "#b00000", 3), (0, "#ff3b35", 1)):
            p.setPen(QPen(QColor(shade), width))
            p.drawText(self.rect().adjusted(20+offset, 0, -20, 0), Qt.AlignmentFlag.AlignCenter, self.title.upper())
        p.setPen(QColor("#6a0909"))
        p.drawLine(0, self.height()-1, self.width(), self.height()-1)


class PhotoJob(QThread):
    ready = Signal(object, int)
    failed = Signal(str)

    def __init__(self, path: str, settings: dict):
        super().__init__()
        self.path, self.settings = path, dict(settings)

    def run(self):
        try:
            with Image.open(self.path) as file:
                source = file.convert("RGB")
            if max(source.size) > 8192:
                source.thumbnail((8192, 8192))
            boxes = Detector().detect(source, self.settings)
            custom = None
            if self.settings["style"] == "Custom image" and self.settings["custom_image"]:
                with Image.open(self.settings["custom_image"]) as file:
                    custom = file.convert("RGB")
            self.ready.emit(censor_image(source, boxes, self.settings, custom), len(boxes))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = SettingsStore()
        self.worker = None
        self.photo_job = None
        self.photo = None
        self.export_message = "Ready — add a photo to begin."
        self.overlays = {}
        self.page_name = "Home"
        self.frames = 0
        self.last_ms = 0
        self.scan_feedback = "Start blocking to measure the actual scan rate."
        self.status = "Ready to protect"
        self.retired_workers = []
        self.overlay_test_timer = QTimer(self)
        self.overlay_test_timer.setSingleShot(True)
        self.overlay_test_timer.timeout.connect(self.stop_protection)
        self.restart_timer = QTimer(self)
        self.restart_timer.setSingleShot(True)
        self.restart_timer.setInterval(200)
        self.restart_timer.timeout.connect(self.start_protection)
        self.interval_save_timer = QTimer(self)
        self.interval_save_timer.setSingleShot(True)
        self.interval_save_timer.setInterval(200)
        self.interval_save_timer.timeout.connect(self.store.save)
        self.display_signals = []
        QApplication.instance().screenAdded.connect(self._display_changed)
        QApplication.instance().screenRemoved.connect(self._display_changed)
        self.setWindowTitle("Veil — Windows")
        self.setMinimumSize(1000, 700)
        self.resize(1260, 820)
        self.setStyleSheet(CSS)
        self.show_page("Home")

    def _changed(self, **changes):
        self.store.update(**changes)
        if self.page_name == "Censor Styles" and hasattr(self, "style_preview"):
            self.style_preview.setPixmap(self._style_preview())
        if self.worker is not None:
            if "monitor" in changes:
                self.stop_protection()
                self.restart_timer.start()
            else:
                self.worker.set_settings(self.store.current, reload_custom="custom_image" in changes)

    def show_page(self, name):
        self.page_name = name
        root = QWidget()
        root.setObjectName("root")
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("QFrame{background:#111;border-right:1px solid #303030}")
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(14, 23, 14, 20)
        nav.setSpacing(5)
        title = text("VEIL", "headline")
        title.setStyleSheet("color:#ef3b36;font-size:28px;letter-spacing:4px")
        nav.addWidget(title)
        nav.addWidget(text("WINDOWS EDITION", "eyebrow"))
        nav.addSpacing(26)
        for page in ("Home", "Body Parts", "Censor Styles", "Export", "Settings", "Help"):
            tab = button(page, lambda checked=False, p=page: self.show_page(p), checkable=True)
            tab.setObjectName("nav")
            tab.setChecked(page == name)
            nav.addWidget(tab)
        nav.addStretch()
        nav.addWidget(text("LOCAL DETECTION  ·  v0.4", "muted"))
        outer.addWidget(sidebar)
        main = QWidget()
        column = QVBoxLayout(main)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(StarHeader({"Home":"Veil Your Screen","Body Parts":"Select Body Parts",
            "Censor Styles":"Change Censor Styles","Export":"Export Photos",
            "Settings":"Configure Veil","Help":"Help & Limits"}[name]))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("page")
        content = QVBoxLayout(body)
        content.setContentsMargins(30, 22, 30, 40)
        content.setSpacing(16)
        getattr(self, "page_" + name.lower().replace(" ", "_"))(content)
        content.addStretch()
        scroll.setWidget(body)
        column.addWidget(scroll)
        outer.addWidget(main, 1)
        self.setCentralWidget(root)

    def page_home(self, layout):
        frame, section = card("SCREEN PROTECTION", "On-device detection with a separate transparent overlay on each selected monitor.")
        self.home_status = text(self.status, "headline")
        section.addWidget(self.home_status)
        self.home_stats = text(f"{self.frames} frames checked  ·  {self.last_ms} ms last pass", "muted")
        section.addWidget(self.home_stats)
        self.home_scan_feedback = text(self.scan_feedback, "muted")
        section.addWidget(self.home_scan_feedback)
        self.home_toggle = button("STOP BLOCKING" if self.worker else "START BLOCKING", self.toggle,
                                  primary=True)
        section.addWidget(self.home_toggle)
        section.addWidget(button("Test overlay (3 seconds)", self.test_overlay))
        section.addWidget(text("The overlay test displays a labeled red rectangle on each selected screen. "
                               "Default categories cover exposed nudity; enable Faces on Body Parts to cover faces.", "muted"))
        layout.addWidget(frame)
        frame, section = card("SCAN FREQUENCY", "Choose the time between scans of every selected display. Changes apply while blocking.")
        self.scan_interval_label = text(interval_label(self.store.current["scan_interval_ms"]), "headline")
        section.addWidget(self.scan_interval_label)
        self.scan_interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.scan_interval_slider.setObjectName("scan_interval")
        self.scan_interval_slider.setRange(0, 1000)
        self.scan_interval_slider.setSingleStep(10)
        self.scan_interval_slider.setPageStep(50)
        self.scan_interval_slider.setValue(self.store.current["scan_interval_ms"])
        self.scan_interval_slider.setAccessibleName("Screen scan interval in milliseconds; zero is fastest")
        self.scan_interval_slider.valueChanged.connect(self._scan_interval)
        section.addWidget(self.scan_interval_slider)
        row = QHBoxLayout()
        fast = text("Faster · more CPU use", "muted")
        fast.setWordWrap(False)
        row.addWidget(fast)
        row.addStretch()
        slow = text("Slower · less CPU use", "muted")
        slow.setWordWrap(False)
        row.addWidget(slow)
        section.addLayout(row)
        section.addWidget(text("Start around 150–200 ms. If games or videos stutter, move toward 250–500 ms. "
                               "Fastest uses the most scanning time. The actual rate is limited by how long each scan takes.", "muted"))
        layout.addWidget(frame)
        frame, section = card("SOURCE", "Choose a display. Use All monitors to cover every connected screen.")
        self.monitor_names = self._monitors()
        combo = QComboBox()
        combo.addItems(["All monitors"] + [label for _, label in self.monitor_names])
        combo.setCurrentText(self.store.current["monitor"] if self.store.current["monitor"] in
                             [combo.itemText(i) for i in range(combo.count())] else "All monitors")
        combo.currentTextChanged.connect(lambda value: self._changed(monitor=value))
        section.addWidget(combo)
        layout.addWidget(frame)
        frame, section = card("CURRENT LOOK")
        section.addWidget(text(f"{self.store.current['style']}  ·  {len(self.store.current['categories'])} categories  ·  "
                               f"{self.store.current['confidence']}% confidence", "headline"))
        section.addWidget(button("Adjust censor style", lambda: self.show_page("Censor Styles")))
        layout.addWidget(frame)

    def _scan_interval(self, value):
        self.scan_interval_label.setText(interval_label(value))
        self.store.current["scan_interval_ms"] = value
        if self.worker is not None:
            self.worker.set_settings(self.store.current)
        # Apply while dragging, but avoid a disk write for every slider tick.
        self.interval_save_timer.start()

    def _monitors(self):
        try:
            import mss
            with mss.mss() as screen:
                return [(i, f"Monitor {i} ({m['width']}×{m['height']})")
                        for i, m in enumerate(screen.monitors) if i]
        except Exception:
            return []

    def page_body_parts(self, layout):
        frame, row = card("PROFILE", "Keep separate category selections for different sessions.")
        line = QHBoxLayout()
        profiles = QComboBox()
        profiles.addItems(self.store.profiles.keys())
        profiles.setCurrentText(self.store.active)
        profiles.currentTextChanged.connect(self._profile)
        line.addWidget(profiles, 1)
        line.addWidget(button("+ New", self._new_profile))
        line.addWidget(button("Delete", self._delete_profile))
        row.addLayout(line)
        inverse = QCheckBox("Reverse censor — hide the surrounding screen")
        inverse.setChecked(self.store.current["inverse"])
        inverse.toggled.connect(lambda on: self._changed(inverse=on))
        row.addWidget(inverse)
        layout.addWidget(frame)
        grid = QGridLayout()
        grid.setSpacing(14)
        for index, (group, category_ids) in enumerate(GROUPS.items()):
            frame, section = card(group)
            if group == "FACES":
                check = QCheckBox("Faces (all people)")
                check.setChecked(any(c in self.store.current["categories"] for c in (1, 12)))
                check.toggled.connect(self._faces_category)
                section.addWidget(check)
                section.addWidget(button("Use faces only", self._faces_only))
                section.addWidget(text("Face-only filtering skips body detection for quicker face updates. "
                                       "Use the category checkbox to keep other selected filters.", "muted"))
                grid.addWidget(frame, index//2, index%2)
                continue
            for category in category_ids:
                check = QCheckBox(LABELS[category])
                check.setChecked(category in self.store.current["categories"])
                check.toggled.connect(lambda on, c=category: self._category(c, on))
                section.addWidget(check)
            grid.addWidget(frame, index//2, index%2)
        layout.addLayout(grid)

    def _faces_category(self, enabled):
        selected = set(self.store.current["categories"]).difference((1, 12))
        if enabled:
            selected.update((1, 12))
        self._changed(categories=sorted(selected))

    def _faces_only(self):
        self._changed(categories=[1, 12])
        self.show_page("Body Parts")

    def _category(self, category, enabled):
        selected = set(self.store.current["categories"])
        selected.add(category) if enabled else selected.discard(category)
        self._changed(categories=sorted(selected))

    def _profile(self, name):
        if name != self.store.active:
            self.store.active = name
            self.store.save()
            self._apply_profile()
            self.show_page("Body Parts")

    def _new_profile(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New profile", "Profile name")
        name = name.strip()[:40]
        if ok and name and name not in self.store.profiles:
            self.store.profiles[name] = dict(self.store.current)
            self.store.active = name
            self.store.save()
            self._apply_profile()
            self.show_page("Body Parts")

    def _delete_profile(self):
        if self.store.active == "Default":
            QMessageBox.information(self, "Default profile", "The Default profile cannot be deleted.")
            return
        del self.store.profiles[self.store.active]
        self.store.active = "Default"
        self.store.save()
        self._apply_profile()
        self.show_page("Body Parts")

    def _apply_profile(self):
        if self.worker is not None:
            self.stop_protection()
            self.restart_timer.start()

    def page_censor_styles(self, layout):
        frame, section = card("LIVE PREVIEW", "A simulated region; it does not indicate detection accuracy.")
        preview = QFrame()
        preview.setObjectName("preview")
        preview.setMinimumHeight(154)
        row = QHBoxLayout(preview)
        row.setContentsMargins(20, 12, 20, 12)
        sample = QLabel()
        sample.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sample.setPixmap(self._style_preview())
        self.style_preview = sample
        row.addWidget(sample)
        section.addWidget(preview)
        layout.addWidget(frame)

        frame, section = card("CENSOR TYPE")
        grid = QGridLayout()
        for index, style in enumerate(STYLES):
            tile = button(style, lambda checked=False, s=style: self._style(s), checkable=True)
            tile.setMinimumHeight(65)
            tile.setChecked(style == self.store.current["style"])
            grid.addWidget(tile, index//3, index%3)
        section.addLayout(grid)
        layout.addWidget(frame)
        frame, section = card("STYLE CONTROLS")
        section.addWidget(text("Color", "eyebrow"))
        color_row = QHBoxLayout()
        for color in ("#e53935", "#000000", "#ed3c9a", "#7828b8", "#ffffff"):
            swatch = button("●", lambda checked=False, c=color: self._color(c))
            swatch.setStyleSheet(f"color:{color};font-size:24px")
            color_row.addWidget(swatch)
        section.addLayout(color_row)
        coverage = QSlider(Qt.Orientation.Horizontal)
        coverage.setRange(-40, 70)
        coverage.setValue(self.store.current["coverage"])
        coverage_label = text(f"Censor coverage: {coverage.value():+d}%", "headline")
        coverage.valueChanged.connect(lambda value: (coverage_label.setText(f"Censor coverage: {value:+d}%"),
                                               self._changed(coverage=value)))
        section.addWidget(coverage_label)
        section.addWidget(coverage)
        section.addWidget(text("Negative values shrink each detected box; −40% leaves 20% of its width and height.", "muted"))
        if self.store.current["style"] == "Pixelated Blur":
            block = QSpinBox()
            block.setRange(4, 64)
            block.setValue(self.store.current["pixel_size"])
            block.valueChanged.connect(lambda value: self._changed(pixel_size=value))
            section.addWidget(text("Pixel block size · larger blocks hide more detail", "eyebrow"))
            section.addWidget(block)
        if self.store.current["style"] == "Labeled":
            label = QLineEdit(self.store.current["label"])
            label.setMaxLength(32)
            label.textChanged.connect(lambda value: self._changed(label=value))
            section.addWidget(label)
        if self.store.current["style"] == "Custom image":
            section.addWidget(button("Choose image…", self._choose_custom))
            section.addWidget(text(self.store.current["custom_image"] or "No image selected", "muted"))
        if self.store.current["style"] in ("Pixelated Blur", "Outline"):
            section.addWidget(text("Border color", "eyebrow"))
            colors = QHBoxLayout()
            for color in ("#ff4545", "#ffffff", "#ed3c9a", "#a0ed5b"):
                b = button("●", lambda checked=False, c=color: self._border(c))
                b.setStyleSheet(f"color:{color};font-size:24px")
                colors.addWidget(b)
            section.addLayout(colors)
        if self.store.current["style"] == "Outline":
            section.addWidget(text("Outline marks detections and leaves the content visible.", "muted"))
        layout.addWidget(frame)

    def _style_preview(self):
        from PySide6.QtGui import QPixmap
        settings = self.store.current
        source = Image.new("RGB", (520, 140), "#171717")
        painter = ImageDraw.Draw(source)
        for x in range(0, 520, 24):
            painter.rectangle((x, 15, x+24, 124), fill=(50+(x*3)%150, 40+(x*5)%125, 70+(x*7)%130))
        coverage = max(-40, min(70, settings["coverage"])) / 100
        margin_x, margin_y = 300*coverage, 70*coverage
        box = Box(max(0, round(110-margin_x)), max(0, round(35-margin_y)),
                  min(520, round(410+margin_x)), min(140, round(105+margin_y)), 1.0, 3)
        custom = None
        if settings["style"] == "Custom image" and settings["custom_image"]:
            try:
                with Image.open(settings["custom_image"]) as file:
                    custom = file.convert("RGB")
            except OSError:
                pass
        result = censor_image(source, [box], settings, custom)
        return QPixmap.fromImage(qimage(result)).scaled(520, 140,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def _style(self, style):
        self._changed(style=style)
        self.show_page("Censor Styles")

    def _color(self, color):
        self._changed(color=color)
        self.show_page("Censor Styles")

    def _border(self, color):
        self._changed(border_color=color)
        self.show_page("Censor Styles")

    def _choose_custom(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose censor image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            # Import a private bounded copy so the selection survives moving the source file.
            try:
                with Image.open(path) as file:
                    image = file.convert("RGB")
                image.thumbnail((512, 512))
                destination = self.store.path.parent / "custom-mask.png"
                destination.parent.mkdir(parents=True, exist_ok=True)
                image.save(destination)
                self._changed(custom_image=str(destination))
                self.show_page("Censor Styles")
            except OSError as exc:
                QMessageBox.warning(self, "Image import failed", str(exc))

    def page_export(self, layout):
        frame, section = card("EXPORT A PHOTO", "Choose a local image, inspect its censored preview, then save a PNG.")
        self.photo_pick = button("+ Add photo", self._pick_photo, primary=True)
        self.photo_pick.setEnabled(self.photo_job is None or not self.photo_job.isRunning())
        section.addWidget(self.photo_pick)
        section.addWidget(text("Original images remain local. Images above 8192 px are reduced before export. Review missed detections before sharing.", "muted"))
        self.export_status = text(self.export_message)
        section.addWidget(self.export_status)
        self.photo_preview = QLabel()
        self.photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_preview.setMinimumHeight(240)
        self.photo_preview.setStyleSheet("background:#0a0a0a;border:1px solid #303030")
        section.addWidget(self.photo_preview)
        if self.photo is not None:
            self._render_photo_preview()
        self.save_button = button("Save censored PNG", self._save_photo, primary=True)
        self.save_button.setEnabled(self.photo is not None)
        section.addWidget(self.save_button)
        layout.addWidget(frame)
        frame, section = card("VIDEO & RECORDING")
        section.addWidget(text("Video export, live recording and OBS virtual camera are not in this build.", "muted"))
        layout.addWidget(frame)

    def _pick_photo(self):
        if self.photo_job is not None and self.photo_job.isRunning():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        self.export_message = "Detecting and rendering on this PC…"
        self.export_status.setText(self.export_message)
        self.photo_pick.setEnabled(False)
        self.photo_job = PhotoJob(path, self.store.current)
        self.photo_job.ready.connect(self._photo_ready)
        self.photo_job.failed.connect(self._photo_failed)
        self.photo_job.finished.connect(self._photo_finished)
        self.photo_job.start()

    def _photo_ready(self, image, count):
        self.photo = image
        message = f"{count} detections · {image.width} × {image.height}. Review for missed regions."
        if self.photo_job.settings["style"] == "Outline":
            message += " Outline only — content remains visible."
        self.export_message = message
        if self.page_name == "Export":
            self.export_status.setText(message)
            self.save_button.setEnabled(True)
            self._render_photo_preview()

    def _photo_failed(self, error):
        self.export_message = "Photo failed: " + error
        if self.page_name == "Export":
            self.export_status.setText(self.export_message)

    def _photo_finished(self):
        if self.page_name == "Export":
            self.photo_pick.setEnabled(True)

    def _render_photo_preview(self):
        image = qimage(self.photo)
        from PySide6.QtGui import QPixmap
        self.photo_preview.setPixmap(QPixmap.fromImage(image).scaled(780, 430,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _save_photo(self):
        if self.photo is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save censored image", "veil-censored.png", "PNG (*.png)")
        if path:
            try:
                self.photo.save(path, format="PNG")
                self.export_message = f"Saved {Path(path).name}"
                self.export_status.setText(self.export_message)
            except OSError as exc:
                QMessageBox.warning(self, "Export failed", str(exc))

    def page_settings(self, layout):
        frame, section = card("DETECTION", "Tune what counts as a detection.")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(20, 90)
        slider.setValue(self.store.current["confidence"])
        value = text(f"Confidence threshold: {slider.value()}%", "headline")
        slider.valueChanged.connect(lambda n: (value.setText(f"Confidence threshold: {n}%"), self._changed(confidence=n)))
        section.addWidget(value)
        section.addWidget(slider)
        section.addWidget(text("Lower values catch more candidates and may increase false positives.", "muted"))
        prediction = QCheckBox("Motion prediction — follow detected regions between scans")
        prediction.setChecked(self.store.current["motion_prediction"])
        prediction.toggled.connect(lambda on: self._changed(motion_prediction=on))
        section.addWidget(prediction)
        section.addWidget(text("Prediction follows recent motion and briefly holds missed detections. "
                               "It cannot cover a new face before detection. Turn it off if masks drift.", "muted"))
        layout.addWidget(frame)
        frame, section = card("PRIVACY & DISPLAY")
        section.addWidget(text("Inference stays on your PC. Veil does not send frames or photos to a server. "
                               "Captured screens remain in memory and are not recorded automatically.", "muted"))
        section.addWidget(text("Click-through overlays are hidden from supported Windows capture paths. "
                               "If overlay exclusion fails, protection stops with an error.", "muted"))
        layout.addWidget(frame)

    def page_help(self, layout):
        frame, section = card("GET STARTED")
        for line in ("1. Select the categories on Body Parts.", "2. Choose a monitor and style.",
                     "3. Test overlay to check visible placement, then press Start Blocking.",
                     "4. For a harmless recognition test, enable Faces, then display a clear portrait. Use faces only for quicker face updates.",
                     "5. Scanning with no matches means frames are being processed but no selected category met the confidence threshold."):
            section.addWidget(text(line))
        layout.addWidget(frame)
        frame, section = card("DIAGNOSTICS")
        section.addWidget(text("If the overlay test is invisible or capture stops, inspect %APPDATA%\\Veil\\diagnostics.log. "
                               "This bounded local log records errors and display geometry; it does not record captured images.", "muted"))
        layout.addWidget(frame)
        frame, section = card("LIMITATIONS")
        for line in ("Capture and overlays need Windows 10 version 2004 or newer, 64-bit.",
                     "Protected video, exclusive fullscreen games and secure desktops may not be captured.",
                     "Detection takes time and may miss regions. The current CPU model does not guarantee coverage before pixels appear.",
                     "Monitor alignment, mixed display scaling and video behavior need testing on a Windows PC.",
                     "This is an independent Veil app; it does not include the original product's assets or paid features."):
            section.addWidget(text(line, "muted"))
        layout.addWidget(frame)

    def toggle(self):
        if self.worker:
            self.stop_protection()
        else:
            self.start_protection()

    def start_protection(self):
        self.restart_timer.stop()
        if self.worker is not None:
            return
        if self.overlay_test_timer.isActive():
            self.stop_protection()
        if not self.store.current["categories"]:
            QMessageBox.warning(self, "No categories", "Choose at least one detection category.")
            return
        try:
            ids = self._create_overlays()
        except Exception as exc:
            LOG.exception("Overlay setup failed")
            self.stop_protection()
            QMessageBox.warning(self, "Overlay unavailable", str(exc))
            return
        self.worker = CaptureThread(self.store.current, ids)
        self.worker.result.connect(self._capture_result)
        self.worker.failure.connect(self._capture_failed)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()
        self.frames, self.last_ms = 0, 0
        self.scan_feedback = "Measuring scan rate…"
        self.status = "Starting local detector…"
        self.show_page("Home")

    def _create_overlays(self):
        import mss
        with mss.mss() as capture:
            monitors = {i: dict(m) for i, m in enumerate(capture.monitors) if i}
        selected = self.store.current["monitor"]
        ids = [i for i, m in monitors.items() if selected == "All monitors" or
               selected == f"Monitor {i} ({m['width']}×{m['height']})"]
        if not ids:
            raise RuntimeError("The selected display is unavailable. Choose a connected display on Home.")
        screens = match_screens({i: monitors[i] for i in ids}, QApplication.screens(), display_devices())
        for monitor_id, screen in screens.items():
            overlay = Overlay(screen)
            self.overlays[monitor_id] = overlay  # Retain even if activation fails, for cleanup.
            overlay.activate()
            for signal in (screen.geometryChanged, screen.logicalDotsPerInchChanged):
                signal.connect(self._display_changed)
                self.display_signals.append(signal)
        return ids

    def test_overlay(self):
        self.stop_protection()
        try:
            self._create_overlays()
            settings = {**self.store.current, "style": "Labeled", "label": "VEIL OVERLAY TEST",
                        "color": RED, "inverse": False, "motion_prediction": False}
            for overlay in self.overlays.values():
                overlay.update_result([Box(300, 400, 700, 600, 1, 1)], [], (1000, 1000), settings)
            self.status = "Overlay test — look for a red rectangle on each selected display"
            self.overlay_test_timer.start(3000)
            self.show_page("Home")
        except Exception as exc:
            LOG.exception("Overlay test failed")
            self.stop_protection()
            QMessageBox.warning(self, "Overlay test failed", str(exc))

    def _display_changed(self, *args):
        if self.overlays:
            self.stop_protection()
            self.status = "Display layout changed — restart blocking to realign overlays"
            self.show_page("Home")

    def _capture_result(self):
        worker = self.sender()
        if worker is not self.worker:
            return
        result = worker.take_result()
        if result is None:
            return
        results, frames, elapsed, settings, timing = result
        self.frames, self.last_ms = frames, elapsed
        rate = (f"{timing.scans_per_second:.1f} scans/sec" if timing.scans_per_second is not None
                else "Measuring scan rate…")
        self.scan_feedback = f"{rate} · {timing.work_ms:.0f} ms average scan work"
        if settings["scan_interval_ms"] == 0:
            self.scan_feedback += " · fastest mode uses the most scanning time"
        elif timing.work_ms > settings["scan_interval_ms"]:
            self.scan_feedback += " · scan time exceeds your interval; rate is limited"
        count = 0
        for monitor_id, boxes, patches, size, captured_at in results:
            if monitor_id in self.overlays:
                self.overlays[monitor_id].update_result(boxes, patches, size, settings, captured_at)
                count += len(boxes)
        self.status = (f"Blocking · {count} detections" if count else "Scanning · no selected categories detected")
        if settings["style"] == "Outline":
            self.status += " · outline only, content remains visible"
        if self.page_name == "Home":
            self.home_status.setText(self.status)
            self.home_stats.setText(f"{self.frames} frames checked  ·  {self.last_ms} ms last pass")
            self.home_scan_feedback.setText(self.scan_feedback)

    def _capture_failed(self, message):
        if self.sender() is not self.worker:
            return
        self.stop_protection()
        self.status = message
        self.show_page("Home")

    def stop_protection(self):
        self.restart_timer.stop()
        self.overlay_test_timer.stop()
        worker, self.worker = self.worker, None
        if worker is not None:
            self.retired_workers.append(worker)
            worker.stop()
            # The finished signal releases it; never destroy a running QThread.
        for signal in self.display_signals:
            try:
                signal.disconnect(self._display_changed)
            except (RuntimeError, TypeError):
                pass
        self.display_signals.clear()
        for overlay in self.overlays.values():
            overlay.hide()
            overlay.deleteLater()
        self.overlays.clear()
        self.status = "Protection stopped"
        self.scan_feedback = "Start blocking to measure the actual scan rate."
        if self.page_name == "Home":
            self.show_page("Home")

    def _worker_finished(self):
        worker = self.sender()
        if worker is self.worker:
            self.stop_protection()
        if worker in self.retired_workers:
            self.retired_workers.remove(worker)
        worker.deleteLater()

    def closeEvent(self, event):
        if self.interval_save_timer.isActive():
            self.interval_save_timer.stop()
            self.store.save()
        self.stop_protection()
        if any(worker.isRunning() for worker in self.retired_workers) or (
                self.photo_job is not None and self.photo_job.isRunning()):
            event.ignore()
            self.status = "Finishing local work before closing…"
            QTimer.singleShot(100, self.close)
            return
        super().closeEvent(event)


def main():
    configure_logging()
    if sys.platform == "win32":
        # Request physical pixels for reliable capture and monitor mapping.
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("Veil")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
