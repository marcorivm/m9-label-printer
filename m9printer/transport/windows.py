"""Windows: RFCOMM through Winsock, via Python's socket module (3.9+).

Untested on real hardware by the author — the protocol is the same bytes as
macOS, only the socket differs. Pair the printer in Settings → Bluetooth first.
"""
import json
import re
import socket
import subprocess

from . import TransportError, to_colons


def send(addr, data, channel, log):
    addr = to_colons(addr)
    try:
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    except (AttributeError, OSError) as e:
        raise TransportError(f"This Python has no Bluetooth socket support ({e}).") from e
    try:
        s.settimeout(15)
        log(f"connecting {addr} channel {channel}…")
        s.connect((addr, channel))
        s.sendall(data)
        log(f"wrote {len(data)}")
    except OSError as e:
        raise TransportError(f"Couldn't send to the printer ({e}). Check it's on, paired "
                             "in Settings → Bluetooth, and not connected to a phone.") from e
    finally:
        s.close()


def paired_devices():
    # Paired classic-Bluetooth devices carry their address in the PnP instance id
    # (…\DEV_414286991A7E…). No extra packages needed.
    ps = ("Get-PnpDevice -Class Bluetooth | Where-Object { $_.InstanceId -match 'DEV_' } | "
          "Select-Object FriendlyName, InstanceId | ConvertTo-Json")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        rows = json.loads(out or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []
    if isinstance(rows, dict):
        rows = [rows]
    devices, seen = [], set()
    for r in rows:
        m = re.search(r"DEV_([0-9A-F]{12})", r.get("InstanceId") or "", re.I)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            a = ":".join(m.group(1)[i:i + 2] for i in range(0, 12, 2)).upper()
            devices.append((r.get("FriendlyName") or a, a))
    return devices
