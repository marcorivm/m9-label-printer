"""Remember the last printer and placement between runs (a small JSON file)."""
import json
import os
import sys

from . import DEFAULT_ADDR

DEFAULTS = {"addr": DEFAULT_ADDR, "width_mm": 101.6, "nudge_mm": 0.0, "density": "normal",
            "feed": "label"}


def _dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "m9printer")


PATH = os.path.join(_dir(), "settings.json")


def load():
    """Saved settings over the defaults; unknown or broken files fall back quietly."""
    try:
        with open(PATH, encoding="utf-8") as f:
            saved = json.load(f)
        return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save(settings):
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump({k: settings[k] for k in DEFAULTS if k in settings}, f, indent=2)
    except OSError:
        pass  # Not being able to remember settings shouldn't stop a print.
