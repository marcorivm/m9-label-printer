"""Linux (BlueZ): RFCOMM straight from Python's socket module.

Untested on real hardware by the author — the protocol is the same bytes as
macOS, only the socket differs. Pair the printer first (bluetoothctl or the
desktop's Bluetooth settings).
"""
import os
import re
import socket
import struct
import subprocess

from . import TransportError, to_colons


AF_BLUETOOTH, BTPROTO_RFCOMM = 31, 3     # <bluetooth/bluetooth.h>, stable kernel ABI


def _connect_libc(addr, channel):
    """RFCOMM connect through libc, for Pythons built without BlueZ headers
    (socket.AF_BLUETOOTH missing). sockaddr_rc = family, bdaddr (reversed), channel."""
    import ctypes
    import ctypes.util
    s = socket.socket(AF_BLUETOOTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
    bdaddr = bytes(int(b, 16) for b in reversed(addr.split(":")))
    sa = struct.pack("<H6sBx", AF_BLUETOOTH, bdaddr, channel)  # padded to C's 10 bytes
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    buf = ctypes.create_string_buffer(sa, len(sa))
    if libc.connect(s.fileno(), buf, len(sa)) != 0:
        err = ctypes.get_errno()
        s.close()
        raise OSError(err, os.strerror(err))
    return s


def send(addr, data, channel, log):
    addr = to_colons(addr)
    log(f"connecting {addr} channel {channel}…")
    try:
        if hasattr(socket, "AF_BLUETOOTH"):
            s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            s.settimeout(15)
            s.connect((addr, channel))
        else:
            s = _connect_libc(addr, channel)
            s.settimeout(15)
    except OSError as e:
        raise TransportError(f"Couldn't connect to the printer ({e}). Check it's on, paired, "
                             "and not connected to a phone.") from e
    try:
        s.sendall(data)
        log(f"wrote {len(data)}")
    except OSError as e:
        raise TransportError(f"Couldn't send to the printer ({e}). Check it's on, paired, "
                             "and not connected to a phone.") from e
    finally:
        s.close()


def paired_devices():
    # Newer bluetoothctl takes "devices Paired"; older ones have "paired-devices".
    for args in (["bluetoothctl", "devices", "Paired"], ["bluetoothctl", "paired-devices"]):
        try:
            out = subprocess.run(args, capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.TimeoutExpired):
            return []
        found = re.findall(r"Device ([0-9A-F:]{17}) (.+)", out, re.I)
        if found:
            return [(name.strip(), to_colons(a)) for a, name in found]
    return []
