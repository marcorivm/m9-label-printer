"""m9printer — print full-width 4x6 labels to the Milestone/Meihengtong M9
(A4 thermal) over Bluetooth, from macOS, Windows or Linux.

The M9's USB port only speaks basic ESC/POS (capped ~48 mm wide). Its real
full-width protocol is Bluetooth-only: JBIG-compressed raster bands, reverse-
engineered from the `com.mht.docprinter` Android app. This package reproduces it.
"""

__version__ = "0.1.0"

# Default Bluetooth address of the owner's unit; override per device in the UI/CLI.
DEFAULT_ADDR = "41-42-86-99-1A-7E"

__all__ = ["__version__", "DEFAULT_ADDR"]
