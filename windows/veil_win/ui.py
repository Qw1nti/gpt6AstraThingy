"""Fluent-inspired Qt presentation; no capture, detection or overlay policy."""
from functools import lru_cache
import ctypes
import sys

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QStyle, QStyleOptionButton, QStyleOptionSpinBox, QVBoxLayout)

LIGHT = dict(bg="#f9f9f9", side="#f3f3f3", card="#ffffff", input="#fdfdfd", hover="#f0f0f0",
             selected="#e8e8e8", line="#e5e5e5", text="#1b1b1b", dim="#606060",
             accent="#0067c0", accent_hover="#1975c5", on_accent="#ffffff", tint="#eaf3fb",
             warning="#fff4ce", warning_text="#6e4d00", success="#0f7b0f", disabled="#8a8a8a")
DARK = dict(bg="#272727", side="#202020", card="#303030", input="#343434", hover="#3b3b3b",
            selected="#383838", line="#454545", text="#ffffff", dim="#c5c5c5",
            accent="#60cdff", accent_hover="#7ad5ff", on_accent="#003e57", tint="#253a46",
            warning="#433c24", warning_text="#fce19b", success="#6ccb5f", disabled="#969696")


def is_dark(mode):
    if mode != "System":
        return mode == "Dark"
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                return not bool(winreg.QueryValueEx(key, "AppsUseLightTheme")[0])
        except OSError:
            pass
    return QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def apply_theme(window, mode):
    dark = is_dark(mode)
    colors = DARK if dark else LIGHT
    palette = QPalette()
    roles = {"Window": "bg", "WindowText": "text", "Base": "input", "AlternateBase": "card",
             "Text": "text", "Button": "input", "ButtonText": "text", "Highlight": "accent",
             "HighlightedText": "on_accent", "ToolTipBase": "card", "ToolTipText": "text",
             "PlaceholderText": "dim", "Link": "accent"}
    for role, color in roles.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(colors[color]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(colors["disabled"]))
    QApplication.instance().setPalette(palette)
    families = QFontDatabase.families()
    family = next((font for font in ("Segoe UI Variable", "Segoe UI", "DejaVu Sans") if font in families), "sans-serif")
    font = QFont(family)
    font.setPixelSize(14)
    QApplication.instance().setFont(font)
    window.setStyleSheet(stylesheet(colors))
    window.colors = colors
    window.dark = dark
    native_frame(window, dark)


def native_frame(window, dark):
    """Keep the real Windows caption, Snap Layouts and system resize behavior."""
    if sys.platform != "win32":
        return
    try:
        dwm = ctypes.WinDLL("dwmapi")
        dwm.DwmSetWindowAttribute.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint)
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        handle = ctypes.c_void_p(int(window.winId()))
        value = ctypes.c_int(int(dark))
        dwm.DwmSetWindowAttribute(handle, 20, ctypes.byref(value), ctypes.sizeof(value))
        corner = ctypes.c_int(2)  # DWMWCP_ROUND; unsupported systems keep their frame.
        dwm.DwmSetWindowAttribute(handle, 33, ctypes.byref(corner), ctypes.sizeof(corner))
    except (OSError, AttributeError):
        pass


def stylesheet(c):
    return """
QMainWindow, QWidget#root, QWidget#workspace, QWidget#page, QScrollArea { background:%(bg)s; color:%(text)s; }
QWidget { color:%(text)s; font-size:14px; }
QFrame#sidebar { background:%(side)s; border-right:1px solid %(line)s; }
QLabel { background:transparent; border:0; }
QLabel#muted { color:%(dim)s; font-size:12px; }
QLabel#eyebrow, QLabel#section { font-size:14px; font-weight:600; }
QLabel#headline { font-size:20px; font-weight:600; }
QLabel#pageTitle { font-size:28px; font-weight:600; }
QLabel#brand { font-size:20px; font-weight:600; }
QLabel#status { color:%(dim)s; font-size:12px; }
QLabel#status[active=true] { color:%(success)s; }
QFrame#card { background:%(card)s; border:1px solid %(line)s; border-radius:8px; }
QFrame#info { background:%(tint)s; border:1px solid %(line)s; border-radius:6px; }
QFrame#warning { background:%(warning)s; border:1px solid %(line)s; border-radius:6px; }
QFrame#warning QLabel { color:%(warning_text)s; }
QFrame#preview, QLabel#photoPreview { background:%(side)s; border:1px solid %(line)s; border-radius:6px; }
QPushButton { background:%(input)s; border:1px solid %(line)s; border-bottom-color:%(disabled)s;
              border-radius:4px; padding:7px 14px; min-height:18px; }
QPushButton:hover { background:%(hover)s; }
QPushButton:pressed { background:%(selected)s; }
QPushButton:focus, QComboBox:focus, QLineEdit:focus, QSpinBox:focus { border:1px solid %(accent)s; }
QPushButton:disabled { color:%(disabled)s; background:%(side)s; border-color:%(line)s; }
QPushButton#primary { background:%(accent)s; color:%(on_accent)s; border-color:%(accent)s; font-weight:600; }
QPushButton#primary:hover { background:%(accent_hover)s; }
QPushButton#primary:disabled { background:%(selected)s; color:%(disabled)s; border-color:%(line)s; }
QPushButton:checked { background:%(tint)s; border:1px solid %(accent)s; }
QPushButton#nav { background:transparent; border:0; border-left:3px solid transparent;
                  border-radius:4px; text-align:left; padding:10px 12px; min-height:20px; }
QPushButton#nav:hover { background:%(hover)s; }
QPushButton#nav:checked { background:%(selected)s; border-left-color:%(accent)s; font-weight:600; }
QPushButton#nav:focus { border:1px solid %(accent)s; border-left:3px solid %(accent)s; }
QPushButton#link { color:%(accent)s; background:transparent; border:0; text-align:left; padding:4px 0; }
QPushButton#link:hover { text-decoration:underline; }
QPushButton#swatch { padding:3px; border-radius:4px; }
QPushButton#styleTile { text-align:left; padding:12px; min-height:26px; }
QComboBox, QLineEdit, QSpinBox { background:%(input)s; border:1px solid %(line)s;
                              border-bottom-color:%(disabled)s; border-radius:4px; padding:6px 10px; min-height:20px; }
QComboBox { padding-right:24px; }
QComboBox::drop-down { subcontrol-origin:padding; subcontrol-position:top right; width:24px; border:0; }
QComboBox::down-arrow { image:none; width:0; height:0; }
QSpinBox::up-button, QSpinBox::down-button { width:22px; border:0; background:transparent; }
QSpinBox::up-arrow, QSpinBox::down-arrow { image:none; }
QComboBox QAbstractItemView { background:%(card)s; selection-background-color:%(selected)s;
                            selection-color:%(text)s; border:1px solid %(line)s; padding:4px; }
QCheckBox { spacing:10px; min-height:30px; }
QCheckBox::indicator { width:18px; height:18px; border:1px solid %(dim)s; border-radius:4px; background:%(input)s; }
QCheckBox::indicator:hover { background:%(hover)s; }
QCheckBox::indicator:checked { background:%(accent)s; border-color:%(accent)s; }
QCheckBox:focus { outline:1px solid %(accent)s; }
QSlider::groove:horizontal { height:4px; background:%(line)s; border-radius:2px; }
QSlider::sub-page:horizontal { background:%(accent)s; border-radius:2px; }
QSlider::handle:horizontal { width:12px; margin:-8px 0; background:%(accent)s;
                            border:4px solid %(card)s; border-radius:9px; }
QSlider::handle:horizontal:focus { border-color:%(dim)s; }
QScrollBar:vertical { background:transparent; width:8px; margin:4px 1px; }
QScrollBar::handle:vertical { background:%(disabled)s; min-height:32px; border-radius:3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
QToolTip { background:%(card)s; color:%(text)s; border:1px solid %(line)s; padding:6px; }
""" % c


PATHS = {
    "shield": '<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
    "home": '<path d="m3 11 9-8 9 8M5 10v11h5v-7h4v7h5V10"/>',
    "detect": '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/><circle cx="12" cy="10" r="3"/><path d="M7 18c0-5 10-5 10 0"/>',
    "style": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m5 19 14-14M4 12h8m0 0v8"/>',
    "photo": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8" cy="9" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
    "settings": '<path d="m9 3-1 3-3 1-2 4 2 2v3l4 3 3-1 3 1 4-3v-3l2-2-2-4-3-1-1-3Z"/><circle cx="12" cy="11" r="3"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 4 3c-1 0-1 1-1 2m0 3v.1"/>',
    "monitor": '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M12 17v4m-5 0h10"/>',
    "speed": '<path d="M4 18a9 9 0 1 1 16 0M12 13l5-5M5 15h1m0-7 1 1m5-5v1m7 10h-1"/>',
    "chevron": '<path d="m9 5 7 7-7 7"/>',
    "solid": '<rect x="4" y="4" width="16" height="16" rx="2" fill="currentColor"/>',
    "swatch": '<rect x="4" y="4" width="16" height="16" rx="2" fill="currentColor" stroke="#858585" stroke-width=".6"/>',
    "blur": '<circle cx="12" cy="12" r="7"/><path d="M8 6v12m4-13v14m4-13v12" opacity=".5"/>',
    "pixel": '<path d="M4 4h6v6H4Zm10 0h6v6h-6ZM4 14h6v6H4Zm10 0h6v6h-6Z"/>',
    "text": '<path d="M4 5h16M12 5v15m-4 0h8"/>',
    "outline": '<rect x="4" y="4" width="16" height="16" rx="2" stroke-dasharray="4 3"/>',
    "folder": '<path d="M3 7V5h7l2 3h9v12H3V7Z"/>',
}


@lru_cache(maxsize=128)
def icon(name, color, size=20):
    paths = PATHS.get(name, PATHS["shield"]).replace("currentColor", color)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round">{paths}</g></svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(size*3, size*3)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(3)
    return QIcon(pixmap)


def text(value, kind=""):
    label = QLabel(value)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setObjectName(kind)
    return label


def button(label, callback, primary=False, checkable=False):
    control = QPushButton(label)
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    control.setCheckable(checkable)
    control.setObjectName("primary" if primary else "")
    control.clicked.connect(callback)
    return control


def card(title="", subtitle=""):
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)
    if title:
        layout.addWidget(text(title, "section"))
    if subtitle:
        layout.addWidget(text(subtitle, "muted"))
    return frame, layout


def setting_row(title, description, control):
    frame, layout = card()
    row = QHBoxLayout()
    row.setSpacing(24)
    labels = QVBoxLayout()
    labels.setSpacing(4)
    labels.addWidget(text(title, "section"))
    if description:
        labels.addWidget(text(description, "muted"))
    row.addLayout(labels, 1)
    row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
    layout.addLayout(row)
    return frame


def notice(message, warning=False):
    frame = QFrame()
    frame.setObjectName("warning" if warning else "info")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.addWidget(text(message))
    return frame


class CheckBox(QCheckBox):
    """Keep Qt keyboard/accessibility semantics and draw a visible check mark."""
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.isChecked():
            option = QStyleOptionButton()
            self.initStyleOption(option)
            rect = self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, self)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(self.palette().highlightedText().color(), 1.8, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(rect.left()+4, rect.center().y(), rect.left()+8, rect.bottom()-5)
            painter.drawLine(rect.left()+8, rect.bottom()-5, rect.right()-3, rect.top()+5)


class ComboBox(QComboBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().windowText().color(), 1.2, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        x, y = self.width()-16, self.height()//2
        painter.drawLine(x-4, y-2, x, y+2)
        painter.drawLine(x, y+2, x+4, y-2)


class SpinBox(QSpinBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().windowText().color(), 1.2, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        for control, direction in ((QStyle.SubControl.SC_SpinBoxUp, -1), (QStyle.SubControl.SC_SpinBoxDown, 1)):
            rect = self.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, control, self)
            x, y = rect.center().x(), rect.center().y()
            painter.drawLine(x-3, y-direction, x, y+direction)
            painter.drawLine(x, y+direction, x+3, y-direction)


class ToggleSwitch(QCheckBox):
    def __init__(self, name, checked=False):
        super().__init__(name)
        self.setAccessibleName(name)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(92, 34)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = self.palette().highlight().color()
        dim = self.palette().placeholderText().color()
        painter.setPen(QPen(accent if self.isChecked() else dim, 1))
        painter.setBrush(accent if self.isChecked() else Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(1, 6, 40, 21), 10.5, 10.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().highlightedText().color() if self.isChecked() else dim)
        painter.drawEllipse(QRectF(24 if self.isChecked() else 5, 10, 13, 13))
        painter.setPen(self.palette().windowText().color())
        painter.drawText(QRectF(51, 0, 40, 34), Qt.AlignmentFlag.AlignVCenter, "On" if self.isChecked() else "Off")
        if self.hasFocus():
            painter.setPen(QPen(accent, 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(0, 2, 90, 29), 4, 4)
