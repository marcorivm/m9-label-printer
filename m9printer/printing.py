"""One print job, shared by the window and the command line: render, encode, send."""
from . import transport
from .protocol import DENSITY, DPI, FEED, build
from .render import load_content, canvas, placement

MM_PER_IN = 25.4
A4_H_MM = 297


def mm_to_dots(mm):
    return round(mm * DPI / MM_PER_IN)


def compose(content, nudge_mm):
    """Head-wide 1-bit image for already-loaded label content, and whether the nudge was clamped."""
    offset, clamped = placement(content.width, mm_to_dots(nudge_mm))
    return canvas(content, offset=offset), clamped


def prepare(path, width_mm=101.6, nudge_mm=0.0, density="normal", feed="label"):
    """(print stream, head-wide image, nudge clamped?) for a label file."""
    if density not in DENSITY:
        raise ValueError(f"density must be one of {', '.join(DENSITY)}")
    if feed not in FEED:
        raise ValueError(f"feed must be one of {', '.join(FEED)}")
    img, clamped = compose(load_content(path, mm_to_dots(width_mm)), nudge_mm)
    return build(img, density, feed), img, clamped


def test_stream(density="normal"):
    """Just the settings preamble: the printer accepts it and prints nothing,
    so it checks the Bluetooth link without using up a label."""
    return DENSITY[density]


def send(addr, stream, log=print):
    transport.send(addr, stream, log=log)
