"""Send a print stream to the M9 over classic-Bluetooth RFCOMM.

The M9 listens on RFCOMM channel 1. Linux and Windows reach it through Python's
own socket module (AF_BLUETOOTH); macOS has no AF_BLUETOOTH in Python, so it
goes through a small IOBluetooth helper (btsend2). The printer must be paired
with the computer first, in the system's Bluetooth settings.
"""
import sys

CHANNEL = 1


class TransportError(RuntimeError):
    """Couldn't reach or write to the printer; the message says what to try."""


def to_colons(addr):
    """'41-42-86-99-1a-7e' or '41:42:…' -> '41:42:86:99:1A:7E'."""
    return addr.strip().replace("-", ":").upper()


def to_dashes(addr):
    """'41:42:86:99:1a:7e' or '41-42-…' -> '41-42-86-99-1A-7E'."""
    return addr.strip().replace(":", "-").upper()


def _backend():
    if sys.platform == "darwin":
        from . import macos as b
    elif sys.platform.startswith("win"):
        from . import windows as b
    else:
        from . import linux as b
    return b


def send(addr, data, channel=CHANNEL, log=print):
    """Connect to the printer at addr and write the whole stream."""
    _backend().send(addr, data, channel, log)


def paired_devices():
    """[(name, address)] of paired Bluetooth devices; [] if the OS won't say."""
    try:
        return _backend().paired_devices()
    except Exception:
        return []
