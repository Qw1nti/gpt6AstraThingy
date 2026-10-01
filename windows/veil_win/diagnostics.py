"""Bounded local operational logs; no captured pixels or source images."""
import logging
from logging.handlers import RotatingFileHandler
import sys

from .settings import config_path


def configure_logging():
    logger = logging.getLogger("veil_win")
    logger.setLevel(logging.INFO)
    try:
        path = config_path().parent / "diagnostics.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=256_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    def unhandled(kind, value, traceback):
        logger.error("Unhandled application error", exc_info=(kind, value, traceback))
        if sys.stderr is not None:
            sys.__excepthook__(kind, value, traceback)
    sys.excepthook = unhandled
