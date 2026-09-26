"""Small, local-only preference store. Never stores captured frames or source photos."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .core import DEFAULT_CATEGORIES

DEFAULT = {
    "categories": list(DEFAULT_CATEGORIES), "confidence": 45, "coverage": 18,
    "style": "Solid Box", "color": "#e53935", "border_color": "#ff4545",
    "pixel_size": 20, "label": "NOPE", "inverse": False,
    "preset": "Medium", "monitor": "All monitors", "custom_image": "",
}
STYLES = ("Solid Box", "Mosaic", "Blur", "Labeled", "Outline", "Custom image")


def config_path() -> Path:
    parent = Path(os.environ.get("APPDATA", Path.home() / ".config")) / "Veil"
    return parent / "settings.json"


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or config_path()
        self.profiles = {"Default": dict(DEFAULT)}
        self.active = "Default"
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                profiles = data.get("profiles", {})
                for name, settings in profiles.items():
                    if isinstance(name, str) and isinstance(settings, dict):
                        self.profiles[name] = {**DEFAULT, **settings}
                self.active = data.get("active", "Default")
                if self.active not in self.profiles:
                    self.active = "Default"
            except (ValueError, OSError, TypeError):
                pass

    @property
    def current(self) -> dict:
        return self.profiles[self.active]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps({"active": self.active, "profiles": self.profiles}, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def update(self, **changes):
        self.current.update(changes)
        self.save()
