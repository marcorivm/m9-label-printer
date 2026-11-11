"""Build the M9 print stream from a 1-bit image.

Reverse-engineered from the com.mht.docprinter app (xi.j.Q / utils.e):

    density-init
    + per band:  1F 01 05  LE16(bytes/row) LE16(rows) LE16(len)  <JBIG BIE>
    + 0A 0A 0A  1F 01 06

Bitmap is 1 = black, MSB-first. JBIG is jbigkit with default options, single
plane (pbmtojbg -q) — the same library (JBIG_Compressing) the app bundles in
libSerialPort.so, confirmed by decompilation.
"""
import os
import struct
import subprocess
import tempfile

from .resources import find_binary

HEAD_W = 1680      # full print width in dots: A4 at 203 dpi (app's xi.j.f46908a)
BAND_ROWS = 100    # rows per JBIG band (app's default)
DPI = 203
LABEL_W = 812      # a 4 in label at 203 dpi

# xi.e.o(gear, settings): 1F FD 01 <code> <val>. Code 08 is the heat level;
# the rest is the app's PrintDensityEnum.NORMAL preamble, identical across gears.
_PREAMBLE = bytes([0x1F, 0xFD, 1, 1, 0x10, 0x1F, 0xFD, 1, 2, 0x64,
                   0x1F, 0xFD, 1, 3, 1, 0x1F, 0xFD, 1, 4, 2, 0x1F, 0xFD, 1, 5, 0])
HEAT = {"low": 130, "normal": 160, "thick": 190}
DENSITY = {k: _PREAMBLE + bytes([0x1F, 0xFD, 1, 8, v]) for k, v in HEAT.items()}


# Paper length, sent before the settings. The vendor app sends 1F 01 07 00 for
# roll paper (stop after the content) and 1F 01 07 DD for single sheets on its A3
# models, and always 00 on the MHT-400/X-131 — but nothing on the M9, which then
# feeds a whole A4 sheet per job (about one extra 4x6 label).
FEED = {"label": bytes.fromhex("1F010700"), "sheet": bytes.fromhex("1F0107DD")}


def _le16(n):
    return struct.pack("<H", n)


def pack_1bpp(img):
    """PIL mode-'1' image -> (bytes_per_row, packed) with 1 = black, MSB first."""
    w, h = img.size
    bpl = (w + 7) // 8
    # Raw mode "1;I" is Pillow's inverted 1-bit packing (1 = black), rows padded
    # to whole bytes — the printer's layout, without a per-pixel Python loop.
    data = img.convert("1").tobytes("raw", "1;I")
    if w % 8:
        # Keep the row padding white, whatever the packer left in it.
        mask = (0xFF << (8 - w % 8)) & 0xFF
        buf = bytearray(data)
        for y in range(h):
            buf[y * bpl + bpl - 1] &= mask
        data = bytes(buf)
    return bpl, data


class MissingTool(RuntimeError):
    """A helper binary the printer needs isn't installed or bundled."""


def jbig(bpl, rows, packed):
    """One band's packed bitmap -> a single-layer JBIG BIE via pbmtojbg."""
    exe = find_binary("pbmtojbg", "M9_PBMTOJBG")
    if not exe:
        raise MissingTool("pbmtojbg (jbigkit) not found — reinstall the app, or "
                          "install jbigkit and put pbmtojbg on PATH.")
    # Files, not pipes: pbmtojbg opens named files in binary mode but leaves
    # stdin/stdout in text mode, which mangles the bytes on Windows.
    with tempfile.TemporaryDirectory(prefix="m9-") as d:
        src, dst = os.path.join(d, "band.pbm"), os.path.join(d, "band.jbg")
        with open(src, "wb") as f:
            f.write(b"P4\n%d %d\n" % (bpl * 8, rows) + packed)
        subprocess.run([exe, "-q", src, dst], check=True, capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        with open(dst, "rb") as f:
            return f.read()


def build(img, density="normal", feed=None):
    """1-bit PIL image (HEAD_W wide) -> the complete M9 print stream.

    feed: "label" (stop after the content), "sheet" (a full A4 page), or None
    to send no paper-length command, as the vendor app does for the M9.
    """
    w, h = img.size
    bpl, packed = pack_1bpp(img)
    out = bytearray(FEED[feed] if feed else b"") + DENSITY[density]
    for y0 in range(0, h, BAND_ROWS):
        rows = min(BAND_ROWS, h - y0)
        bie = jbig(bpl, rows, packed[y0 * bpl:(y0 + rows) * bpl])
        out += b"\x1f\x01\x05" + _le16(bpl) + _le16(rows) + _le16(len(bie)) + bie
    out += b"\x0a\x0a\x0a\x1f\x01\x06"
    return bytes(out)
