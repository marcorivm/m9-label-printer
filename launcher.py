"""Entry point for the packaged app (PyInstaller): always opens the window."""
import sys

from m9printer.gui import main

sys.exit(main())
