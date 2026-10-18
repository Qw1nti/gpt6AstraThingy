"""Independent Windows desktop interface for Veil."""
from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
import sys

from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QSlider, QLineEdit,
    QFileDialog, QMessageBox, QGridLayout, QColorDialog, QSizePolicy)

from .capture import CaptureThread, Overlay, qimage
from .core import Box, Detector, GROUPS, LABELS, censor_image
from .settings import SettingsStore, STYLES
from .displays import display_devices, match_screens
from .diagnostics import configure_logging
from .scanning import interval_label
from .ui import apply_theme, text, button, card, setting_row, notice, icon, CheckBox, ToggleSwitch, ComboBox, SpinBox

LOG = logging.getLogger(__name__)

RED = "#e53935"
PAGES = {
    "Home": ("Home", "home", "Control screen blocking and see what’s running."),
    "Body Parts": ("Detection", "detect", "Choose what Veil should detect and cover."),
    "Censor Styles": ("Appearance", "style", "Choose how detected regions look on your screen."),
    "Export": ("Photos", "photo", "Process a photo locally and save the result."),
    "Help": ("Help", "help", "Get started, troubleshoot and understand the limits."),
    "Settings": ("Settings", "settings", "Personalize Veil and fine-tune detection."),
}
STYLE_NAMES = {"Solid Box": "Solid fill", "Blur": "Blur", "Pixelated Blur": "Pixelate",
               "Labeled": "Text", "Outline": "Outline", "Custom image": "Image"}
STYLE_ICONS = dict(zip(STYLES, ("solid", "blur", "pixel", "text", "outline", "photo")))
STYLE_HELP = {"Solid Box": "Cover detected regions with a solid color.",
              "Blur": "Soften detected regions with a smooth blur.",
              "Pixelated Blur": "Cover detected regions with large pixels and a colored border.",
              "Labeled": "Cover detected regions with a solid color and your own text.",
              "Outline": "Draw a border around detections. The content remains visible.",
              "Custom image": "Cover detected regions with an image from your PC."}


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
        self.export_message = "Choose a photo to begin."
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
        self.setWindowTitle("Veil")
        self.setMinimumSize(820, 600)
        self.resize(1120, 780)
        self.theme_icons = []
        QApplication.instance().setStyle("Fusion")
        apply_theme(self, self.store.appearance)
        self._build_shell()
        QApplication.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        self.show_page("Home")

    def _changed(self, **changes):
        self.store.update(**changes)
        if self.page_name == "Body Parts" and hasattr(self, "category_summary"):
            self.category_summary.setText(f"{self._filter_count()} detection categories selected")
        if self.page_name == "Censor Styles" and hasattr(self, "style_preview"):
            self.style_preview.setPixmap(self._style_preview())
        if self.worker is not None:
            if "monitor" in changes:
                self.stop_protection()
                self.restart_timer.start()
            else:
                self.worker.set_settings(self.store.current, reload_custom="custom_image" in changes)

    def _build_shell(self):
        root = QWidget()
        root.setObjectName("root")
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        nav = QVBoxLayout(self.sidebar)
        nav.setContentsMargins(10, 20, 10, 16)
        nav.setSpacing(5)
        brand = QHBoxLayout()
        brand.setContentsMargins(12, 0, 0, 0)
        self.brand_icon = QLabel()
        self.brand_icon.setFixedSize(28, 28)
        brand.addWidget(self.brand_icon)
        self.brand_name = text("Veil", "brand")
        brand.addWidget(self.brand_name, 1)
        nav.addLayout(brand)
        nav.addSpacing(25)
        self.nav_buttons = {}
        for page, (label, _, _) in PAGES.items():
            if page == "Help":
                nav.addStretch()
                self.side_status = text("Blocking is off", "status")
                self.side_status.setContentsMargins(14, 0, 0, 10)
                nav.addWidget(self.side_status)
            tab = button(label, lambda checked=False, p=page: self.show_page(p), checkable=True)
            tab.setObjectName("nav")
            tab.setAccessibleName(label)
            tab.setToolTip(label)
            tab.setIconSize(QSize(20, 20))
            self.nav_buttons[page] = tab
            nav.addWidget(tab)
        outer.addWidget(self.sidebar)
        main = QWidget()
        main.setObjectName("workspace")
        column = QVBoxLayout(main)
        column.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        column.addWidget(self.scroll)
        outer.addWidget(main, 1)
        self.setCentralWidget(root)
        self._refresh_theme_icons()
        self._sync_sidebar()

    def _refresh_theme_icons(self):
        self.brand_icon.setPixmap(icon("shield", self.colors["accent"], 28).pixmap(28, 28))
        self.setWindowIcon(icon("shield", self.colors["accent"], 32))
        for page, control in self.nav_buttons.items():
            control.setIcon(icon(PAGES[page][1], self.colors["text"]))
        for control, name in self.theme_icons:
            control.setIcon(icon(name, self.colors["text"]))
        if self.page_name == "Home" and hasattr(self, "home_icon"):
            self.home_icon.setPixmap(icon("shield", self.colors["accent"], 42).pixmap(42, 42))

    def _system_theme_changed(self, *_):
        if self.store.appearance == "System":
            self._apply_appearance()

    def _apply_appearance(self):
        apply_theme(self, self.store.appearance)
        self._refresh_theme_icons()
        if self.page_name == "Censor Styles":
            self.style_preview.setPixmap(self._style_preview())

    def _appearance(self, value):
        self.store.appearance = value
        self.store.save()
        self._apply_appearance()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            self._sync_sidebar()
        if self.page_name == "Export" and self.photo is not None and hasattr(self, "photo_preview"):
            self._render_photo_preview()

    def _sync_sidebar(self):
        compact = self.width() < 1000
        self.sidebar.setFixedWidth(72 if compact else 210)
        self.brand_name.setVisible(not compact)
        self.side_status.setVisible(not compact)
        for page, control in self.nav_buttons.items():
            control.setText("" if compact else "  " + PAGES[page][0])

    def show_page(self, name):
        name = next((key for key, value in PAGES.items() if value[0] == name), name)
        previous = self.page_name
        position = self.scroll.verticalScrollBar().value() if previous == name else 0
        self.page_name = name
        self.theme_icons = []
        for page, control in self.nav_buttons.items():
            control.setChecked(page == name)
        body = QWidget()
        body.setObjectName("page")
        outer = QHBoxLayout(body)
        outer.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setMaximumWidth(1040)
        content = QVBoxLayout(container)
        content.setContentsMargins(28, 26, 28, 30)
        content.setSpacing(14)
        content.addWidget(text(PAGES[name][0], "pageTitle"))
        content.addWidget(text(PAGES[name][2], "muted"))
        content.addSpacing(8)
        getattr(self, "page_" + name.lower().replace(" ", "_"))(content)
        content.addStretch()
        outer.addWidget(container, 1)
        outer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        old = self.scroll.takeWidget()
        if old:
            old.deleteLater()
        self.scroll.setWidget(body)
        if previous != name:
            self.nav_buttons[name].setFocus(Qt.FocusReason.OtherFocusReason)
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(position)
                          if self.scroll.widget() is body else None)
        self._refresh_status()

    def _filter_count(self):
        selected = set(self.store.current["categories"])
        return len(selected.difference((1, 12))) + int(bool(selected.intersection((1, 12))))

    def _refresh_status(self):
        active = self.worker is not None
        outline = self.store.current["style"] == "Outline"
        self.side_status.setText("On · outline only" if active and outline else "Blocking is on" if active else "Blocking is off")
        self.side_status.setProperty("active", active)
        self.side_status.style().unpolish(self.side_status)
        self.side_status.style().polish(self.side_status)
        if self.page_name == "Home":
            self.home_state.setText("Outline detection is on" if active and outline else "Screen blocking is on" if active
                                    else "Testing the overlay" if self.overlay_test_timer.isActive() else "Screen blocking is off")
            self.home_status.setText(self.status)
            self.home_stats.setText(f"{self.frames} frames checked  ·  {self.last_ms} ms last scan")
            self.home_scan_feedback.setText(self.scan_feedback)

    def _page_link(self, title, description, page):
        control = button("Open", lambda: self.show_page(page))
        control.setAccessibleName("Open " + title)
        control.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        control.setIcon(icon("chevron", self.colors["text"], 16))
        self.theme_icons.append((control, "chevron"))
        return setting_row(title, description, control)

    def page_home(self, layout):
        frame, section = card()
        row = QHBoxLayout()
        row.setSpacing(16)
        shield = QLabel()
        self.home_icon = shield
        shield.setPixmap(icon("shield", self.colors["accent"], 42).pixmap(42, 42))
        row.addWidget(shield)
        labels = QVBoxLayout()
        self.home_state = text("Screen blocking is off", "headline")
        self.home_status = text(self.status, "muted")
        labels.addWidget(self.home_state)
        labels.addWidget(self.home_status)
        row.addLayout(labels, 1)
        self.home_toggle = button("Stop blocking" if self.worker else "Start blocking", self.toggle, primary=True)
        self.home_toggle.setMinimumWidth(125)
        row.addWidget(self.home_toggle)
        section.addLayout(row)
        self.home_stats = text("", "muted")
        section.addWidget(self.home_stats)
        layout.addWidget(frame)
        if self.store.current["style"] == "Outline":
            layout.addWidget(notice("Outline only: detections are marked, but their content stays visible.", True))
        if not self.store.current["categories"]:
            layout.addWidget(notice("No detection categories selected. Open Detection and choose what to cover.", True))

        frame, section = card("Scan frequency", "Set the time between scans. Changes apply immediately while blocking.")
        self.scan_interval_label = text(interval_label(self.store.current["scan_interval_ms"]), "section")
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
        ends = QHBoxLayout()
        ends.addWidget(text("Fastest · more CPU", "muted"))
        ends.addStretch()
        ends.addWidget(text("1,000 ms · less CPU", "muted"))
        section.addLayout(ends)
        self.home_scan_feedback = text(self.scan_feedback, "muted")
        section.addWidget(self.home_scan_feedback)
        section.addWidget(text("Try 150–200 ms first. Use 250–500 ms if games or videos stutter. Scan work limits the actual rate.", "muted"))
        layout.addWidget(frame)

        layout.addWidget(text("Quick setup", "section"))
        combo = ComboBox()
        combo.setAccessibleName("Display to scan")
        combo.setMaximumWidth(290)
        self.monitor_names = self._monitors()
        combo.addItems(["All monitors"] + [label for _, label in self.monitor_names])
        combo.setCurrentText(self.store.current["monitor"] if self.store.current["monitor"] in
                             [combo.itemText(i) for i in range(combo.count())] else "All monitors")
        combo.currentTextChanged.connect(lambda value: self._changed(monitor=value))
        layout.addWidget(setting_row("Display", "Choose which screens Veil scans.", combo))
        layout.addWidget(self._page_link("Detection categories", f"{self._filter_count()} selected · Profile: {self.store.active}", "Body Parts"))
        layout.addWidget(self._page_link("Censor appearance", STYLE_NAMES[self.store.current["style"]], "Censor Styles"))
        test = button("Test overlay", self.test_overlay)
        layout.addWidget(setting_row("Check overlay placement", "Shows a red rectangle for 3 seconds. Stops an active blocking session.", test))

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
        frame, section = card("Profile", "Save separate settings for different sessions.")
        line = QHBoxLayout()
        profiles = ComboBox()
        profiles.setAccessibleName("Detection profile")
        profiles.addItems(self.store.profiles.keys())
        profiles.setCurrentText(self.store.active)
        profiles.currentTextChanged.connect(self._profile)
        line.addWidget(profiles, 1)
        line.addWidget(button("New profile", self._new_profile))
        delete = button("Delete", self._delete_profile)
        delete.setEnabled(self.store.active != "Default")
        line.addWidget(delete)
        section.addLayout(line)
        layout.addWidget(frame)
        self.category_summary = text(f"{self._filter_count()} detection categories selected", "section")
        layout.addWidget(self.category_summary)
        frame, section = card("Faces", "Cover faces of all people. Enabling this keeps your other category selections.")
        check = CheckBox("Detect faces")
        check.setChecked(any(c in self.store.current["categories"] for c in (1, 12)))
        check.toggled.connect(self._faces_category)
        section.addWidget(check)
        row = QHBoxLayout()
        row.addWidget(text("Need only faces? Skip body detection for quicker face updates.", "muted"), 1)
        row.addWidget(button("Use faces only", self._faces_only))
        section.addLayout(row)
        layout.addWidget(frame)
        for group, ids in GROUPS.items():
            if group == "FACES":
                continue
            title, description = {
                "NSFW — EXPOSED": ("Exposed body areas", "Enabled by default. Select the categories you want to cover."),
                "NSFW — COVERED (OPTIONAL)": ("Covered body areas", "Optional categories for clothed regions."),
                "BODY PARTS": ("Other body areas", "Optional chest, belly, feet and armpit detection."),
            }[group]
            frame, section = card(title, description)
            grid = QGridLayout()
            grid.setHorizontalSpacing(20)
            for index, category in enumerate(ids):
                check = CheckBox(LABELS[category])
                check.setChecked(category in self.store.current["categories"])
                check.toggled.connect(lambda on, c=category: self._category(c, on))
                grid.addWidget(check, index//2, index%2)
            section.addLayout(grid)
            layout.addWidget(frame)
        inverse = ToggleSwitch("Reverse censor", self.store.current["inverse"])
        inverse.toggled.connect(lambda on: self._changed(inverse=on))
        layout.addWidget(setting_row("Reverse censor", "Leave detections visible and cover the surrounding screen. Outline still only marks detections.", inverse))

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
        frame, section = card("Censor effect")
        self.style_buttons = {}
        grid = QGridLayout()
        grid.setSpacing(8)
        for index, style in enumerate(STYLES):
            tile = button(STYLE_NAMES[style], lambda checked=False, s=style: self._style(s), checkable=True)
            tile.setObjectName("styleTile")
            tile.setToolTip(STYLE_HELP[style])
            tile.setAccessibleName(STYLE_NAMES[style] + ". " + STYLE_HELP[style])
            tile.setIcon(icon(STYLE_ICONS[style], self.colors["text"]))
            self.theme_icons.append((tile, STYLE_ICONS[style]))
            tile.setChecked(style == self.store.current["style"])
            self.style_buttons[style] = tile
            grid.addWidget(tile, index//3, index%3)
        section.addLayout(grid)
        section.addWidget(text(STYLE_HELP[self.store.current["style"]], "muted"))
        layout.addWidget(frame)
        frame, section = card("Preview", "Illustrated sample only. This does not test detection accuracy.")
        self.style_preview = QLabel()
        self.style_preview.setObjectName("preview")
        self.style_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.style_preview.setMinimumHeight(170)
        self.style_preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.style_preview.setPixmap(self._style_preview())
        section.addWidget(self.style_preview)
        layout.addWidget(frame)
        if self.store.current["style"] == "Outline":
            layout.addWidget(notice("Outline only marks detections. It does not hide their content, including in saved photos.", True))
        frame, section = card("Coverage", "Adjust how far the mask extends beyond each detected region.")
        top = QHBoxLayout()
        coverage_label = text(f"{self.store.current['coverage']:+d}%", "section")
        top.addWidget(coverage_label, 1)
        coverage = QSlider(Qt.Orientation.Horizontal)
        coverage.setAccessibleName("Censor coverage percentage")
        coverage.setRange(-40, 70)
        coverage.setValue(self.store.current["coverage"])
        reset = button("Reset to 0%", lambda: coverage.setValue(0))
        top.addWidget(reset)
        section.addLayout(top)
        coverage.valueChanged.connect(lambda value: (coverage_label.setText(f"{value:+d}%"), self._changed(coverage=value)))
        section.addWidget(coverage)
        section.addWidget(text("Shrink −40%  ·  Detected size 0%  ·  Expand +70%", "muted"))
        section.addWidget(text("Shrinking reduces coverage. At −40%, only 20% of the original width and height remain.", "muted"))
        layout.addWidget(frame)
        style = self.store.current["style"]
        if style in ("Solid Box", "Labeled") or (self.store.current["inverse"] and style != "Outline"):
            layout.addWidget(self._color_picker("Fill color", "color", ("#e53935", "#000000", "#0067c0", "#ed3c9a", "#ffffff")))
        if style == "Pixelated Blur":
            block = SpinBox()
            block.setAccessibleName("Pixel block size")
            block.setRange(4, 64)
            block.setSuffix(" px")
            block.setValue(self.store.current["pixel_size"])
            block.valueChanged.connect(lambda value: self._changed(pixel_size=value))
            layout.addWidget(setting_row("Pixel size", "Larger blocks hide more detail.", block))
        if style == "Labeled":
            field = QLineEdit(self.store.current["label"])
            field.setAccessibleName("Censor text")
            field.setPlaceholderText("Enter censor text")
            field.setMaxLength(32)
            field.textChanged.connect(lambda value: self._changed(label=value))
            layout.addWidget(setting_row("Censor text", "Up to 32 characters.", field))
        if style == "Custom image":
            frame, section = card("Custom image", "An imported copy stays on this PC.")
            section.addWidget(button("Choose image…", self._choose_custom))
            section.addWidget(text(Path(self.store.current["custom_image"]).name if self.store.current["custom_image"] else "No image selected. A solid fill is used until you choose one.", "muted"))
            layout.addWidget(frame)
        if style in ("Pixelated Blur", "Outline"):
            layout.addWidget(self._color_picker("Border color", "border_color", ("#ff4545", "#ffffff", "#0067c0", "#ed3c9a", "#a0ed5b")))

    def _color_picker(self, title, key, colors):
        frame, section = card(title)
        row = QHBoxLayout()
        for color in colors:
            swatch = button("", lambda checked=False, c=color: self._set_color(key, c), checkable=True)
            swatch.setObjectName("swatch")
            swatch.setFixedSize(34, 34)
            swatch.setIcon(icon("swatch", color, 22))
            swatch.setChecked(self.store.current[key].lower() == color)
            swatch.setAccessibleName(title + " " + color)
            swatch.setToolTip(color)
            row.addWidget(swatch)
        row.addStretch()
        row.addWidget(button("Custom…", lambda: self._custom_color(key)))
        section.addLayout(row)
        section.addWidget(text(self.store.current[key].upper(), "muted"))
        return frame

    def _set_color(self, key, color):
        self._changed(**{key: color})
        self.show_page("Censor Styles")

    def _custom_color(self, key):
        color = QColorDialog.getColor(QColor(self.store.current[key]), self, "Choose color")
        if color.isValid():
            self._set_color(key, color.name())

    def _style_preview(self):
        from PySide6.QtGui import QPixmap
        settings = self.store.current
        source = Image.new("RGB", (520, 160), "#deebf7")
        painter = ImageDraw.Draw(source)
        painter.rounded_rectangle((16, 12, 504, 148), radius=8, fill="#ffffff")
        painter.rounded_rectangle((32, 28, 294, 132), radius=5, fill="#bdd9ee")
        painter.ellipse((126, 40, 170, 84), fill="#517d9e")
        painter.rounded_rectangle((100, 88, 198, 146), radius=30, fill="#517d9e")
        for y, width in ((38, 148), (58, 112), (88, 150), (108, 128)):
            painter.rounded_rectangle((318, y, 318+width, y+7), radius=3, fill="#d4e1ec")
        coverage = max(-40, min(70, settings["coverage"])) / 100
        margin_x, margin_y = 110*coverage, 100*coverage
        box = Box(max(0, round(94-margin_x)), max(0, round(32-margin_y)),
                  min(520, round(204+margin_x)), min(160, round(132+margin_y)), 1.0, 3)
        custom = None
        if settings["style"] == "Custom image" and settings["custom_image"]:
            try:
                with Image.open(settings["custom_image"]) as file:
                    custom = file.convert("RGB")
            except OSError:
                pass
        result = censor_image(source, [box], settings, custom)
        return QPixmap.fromImage(qimage(result)).scaled(520, 160,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def _style(self, style):
        self._changed(style=style)
        self.show_page("Censor Styles")
        self.style_buttons[style].setFocus()

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
        frame, section = card("Photo workspace", "Uses your current detection categories and censor appearance.")
        row = QHBoxLayout()
        self.photo_pick = button("Choose photo…", self._pick_photo, primary=True)
        self.photo_pick.setEnabled(self.photo_job is None or not self.photo_job.isRunning())
        row.addWidget(self.photo_pick)
        self.save_button = button("Save PNG…", self._save_photo)
        self.save_button.setEnabled(self.photo is not None)
        row.addWidget(self.save_button)
        row.addStretch()
        section.addLayout(row)
        section.addWidget(text(f"{self._filter_count()} categories · {STYLE_NAMES[self.store.current['style']]} · {self.store.current['confidence']}% confidence", "muted"))
        self.export_status = text(self.export_message)
        section.addWidget(self.export_status)
        self.photo_preview = QLabel("No photo selected\n\nChoose a photo to detect and preview covered regions.")
        self.photo_preview.setObjectName("photoPreview")
        self.photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_preview.setWordWrap(True)
        self.photo_preview.setMinimumHeight(280)
        self.photo_preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        section.addWidget(self.photo_preview)
        if self.photo is not None:
            self._render_photo_preview()
        layout.addWidget(frame)
        layout.addWidget(notice("Review the processed image before sharing. Detection can miss regions. Outline mode leaves the content visible.", True))
        layout.addWidget(text("Photos stay on this PC. Images larger than 8192 px are reduced. Video export and screen recording are not available.", "muted"))

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
        self.photo_preview.setPixmap(QPixmap.fromImage(image).scaled(max(100, self.photo_preview.width()-24), 400,
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
        layout.addWidget(text("Personalization", "section"))
        theme = ComboBox()
        theme.setAccessibleName("App theme")
        for label, value in (("Use system setting", "System"), ("Light", "Light"), ("Dark", "Dark")):
            theme.addItem(label, value)
        theme.setCurrentIndex(theme.findData(self.store.appearance))
        theme.currentIndexChanged.connect(lambda i: self._appearance(theme.itemData(i)))
        layout.addWidget(setting_row("App theme", "Choose a light or dark interface, or follow Windows.", theme))
        layout.addSpacing(8)
        layout.addWidget(text("Detection behavior", "section"))
        frame, section = card("Confidence threshold", "Lower values catch more candidates and can increase false positives.")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setAccessibleName("Detection confidence percentage")
        slider.setRange(20, 90)
        slider.setValue(self.store.current["confidence"])
        value = text(f"{slider.value()}%", "section")
        slider.valueChanged.connect(lambda n: (value.setText(f"{n}%"), self._changed(confidence=n)))
        section.addWidget(value)
        section.addWidget(slider)
        layout.addWidget(frame)
        prediction = ToggleSwitch("Motion prediction", self.store.current["motion_prediction"])
        prediction.toggled.connect(lambda on: self._changed(motion_prediction=on))
        layout.addWidget(setting_row("Motion prediction", "Follow recent movement between scans and briefly hold missed detections. Turn off if masks drift.", prediction))
        layout.addWidget(text("Prediction cannot cover a face before its first detection or guarantee coverage through scene cuts.", "muted"))
        layout.addSpacing(8)
        frame, section = card("Privacy", "Detection runs on this PC. Frames and source photos are not sent to a server or saved automatically.")
        section.addWidget(text("Click-through overlays are excluded from supported capture paths. Protection stops if Windows cannot exclude them.", "muted"))
        layout.addWidget(frame)
        frame, section = card("About Veil")
        section.addWidget(text("Windows edition · Version 0.5", "muted"))
        section.addWidget(text("Independent desktop app with local detection. Preferences and bounded diagnostic logs are stored in %APPDATA%\\Veil.", "muted"))
        layout.addWidget(frame)

    def page_help(self, layout):
        frame, section = card("Start in three steps")
        for title, detail, page in (
            ("1. Choose what to detect", "Open Detection. Enable faces or select body categories. Use faces only skips the body model.", "Body Parts"),
            ("2. Pick an appearance", "Choose a censor effect and check its sample preview. Outline only marks detections.", "Censor Styles"),
            ("3. Start screen blocking", "On Home, choose a display, test the overlay placement, then start blocking.", "Home")):
            section.addWidget(text(title, "section"))
            section.addWidget(text(detail, "muted"))
            action = button("Open " + PAGES[page][0], lambda checked=False, p=page: self.show_page(p))
            action.setObjectName("link")
            section.addWidget(action)
        layout.addWidget(frame)
        frame, section = card("Blocking is on, but nothing is covered")
        section.addWidget(text("Run Test overlay on Home. If the red rectangle appears, check your categories and confidence threshold. The default categories cover exposed body areas; enable Faces to cover faces."))
        section.addWidget(text("“No selected categories detected” means scanning is running, but no chosen category met the threshold. A clear, static portrait with Faces enabled is a useful test.", "muted"))
        layout.addWidget(frame)
        frame, section = card("Performance and capture")
        for line in ("Start with a 150–200 ms scan interval. If games or videos stutter, try 250–500 ms. Home shows achieved scan rate and average scan work.",
                     "Protected video, exclusive fullscreen games and secure desktops may not be captured. Try a normal window.",
                     "After changing display layout or scaling, restart blocking to recreate aligned overlays.",
                     "Capture requires 64-bit Windows 10 version 2004 or newer. The interface follows Windows 11 styling."):
            section.addWidget(text(line, "muted"))
        layout.addWidget(frame)
        frame, section = card("Diagnostics")
        section.addWidget(text("If capture stops or the overlay test is invisible, check %APPDATA%\\Veil\\diagnostics.log. It records operational errors and display geometry, never captured images.", "muted"))
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
        self._refresh_status()

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
        self._refresh_status()
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
