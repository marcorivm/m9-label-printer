# PyInstaller build for all three platforms:  pyinstaller m9printer.spec
# Expects the helper binaries already built into m9printer/bin/ (CI does this):
#   all:   pbmtojbg        macOS: btsend2, blueutil
import glob
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from m9printer import __version__  # noqa: E402

NAME = "M9 Label Printer"
binaries = [(p, "bin") for p in glob.glob("m9printer/bin/*") if os.path.isfile(p)]

a = Analysis(
    ["launcher.py"],
    binaries=binaries,
    datas=[("THIRD_PARTY_NOTICES.md", ".")],
    hiddenimports=["m9printer.transport.macos", "m9printer.transport.linux",
                   "m9printer.transport.windows"],
    excludes=["unittest", "pydoc", "test"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    # A .app is a folder build; onefile .apps are deprecated.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME, console=False)
    coll = COLLECT(exe, a.binaries, a.datas, name=NAME)
    app = BUNDLE(
        coll,
        name=f"{NAME}.app",
        bundle_identifier="com.marcorivm.m9printer",
        version=__version__,
        info_plist={
            # Without this key macOS terminates the app on its first Bluetooth use.
            "NSBluetoothAlwaysUsageDescription":
                "M9 Label Printer sends your labels to the printer over Bluetooth.",
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": __version__,
            # Lets you drop a label on the app icon or use "Open With".
            "CFBundleDocumentTypes": [{
                "CFBundleTypeName": "Label",
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["com.adobe.pdf", "public.image"],
            }],
        },
    )
else:
    # One file to download and run on Windows and Linux.
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="m9-label-printer",
              console=False)
