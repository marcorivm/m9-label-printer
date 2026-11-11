"""Locate the helper binaries the printer needs (pbmtojbg, and on macOS btsend2
and blueutil), whether running from source or from a frozen PyInstaller build."""
import os
import shutil
import sys

_EXE = ".exe" if os.name == "nt" else ""


def _bundle_dirs():
    """Folders that may hold a bundled binary, most specific first."""
    dirs = []
    # PyInstaller unpacks --add-binary files under sys._MEIPASS/bin.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(os.path.join(meipass, "bin"))
    # From source, binaries we build live next to the package in m9printer/bin.
    dirs.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"))
    return dirs


def find_binary(name, env=None):
    """Path to an executable: env override, then a bundled copy, then PATH.

    Returns None when it can't be found, so callers can explain what's missing.
    """
    if env and os.environ.get(env):
        return os.environ[env]
    for d in _bundle_dirs():
        p = os.path.join(d, name + _EXE)
        if os.path.isfile(p):
            return p
    return shutil.which(name) or shutil.which(name + _EXE)
