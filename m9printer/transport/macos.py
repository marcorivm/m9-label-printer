"""macOS: connect with blueutil, write over IOBluetooth RFCOMM via btsend2.

Python on macOS has no AF_BLUETOOTH, and the /dev/cu.M9 serial bridge macOS
creates does not carry data to this printer — only a real RFCOMM channel does.
The synchronous IOBluetooth open also fails here, so btsend2 opens the channel
asynchronously and runs a run loop (see helpers/btsend2.swift).
"""
import os
import re
import subprocess
import tempfile
import time

from ..resources import find_binary
from . import TransportError, to_dashes


def _blueutil():
    return find_binary("blueutil", "M9_BLUEUTIL")


def send(addr, data, channel, log):
    helper = find_binary("btsend2", "M9_BTSEND2")
    if not helper:
        raise TransportError("The Bluetooth helper (btsend2) is missing — reinstall the app.")
    addr = to_dashes(addr)
    bu = _blueutil()
    if bu:
        # Wake the link first; the RFCOMM open is far more reliable on a live connection.
        subprocess.run([bu, "--connect", addr], capture_output=True)
        time.sleep(1)
    else:
        log("blueutil not found; trying without an explicit connect.")
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        r = subprocess.run([helper, addr, path, str(channel)],
                           capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(path)
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.strip().splitlines():
        log(line)
    m = re.search(r"wrote (\d+)", out)
    if r.returncode != 0 or not m or int(m.group(1)) != len(data):
        raise TransportError("Couldn't send to the printer. Check it's on, paired in "
                             "System Settings → Bluetooth, and not connected to a phone.")


def paired_devices():
    bu = _blueutil()
    if not bu:
        return []
    out = subprocess.run([bu, "--paired"], capture_output=True, text=True).stdout
    devices, seen = [], set()
    for line in out.splitlines():
        a = re.search(r"address: ([0-9a-fA-F-:]{17})", line)
        n = re.search(r'name: "([^"]*)"', line)
        if a and to_dashes(a.group(1)) not in seen:     # blueutil can list a device twice
            seen.add(to_dashes(a.group(1)))
            devices.append((n.group(1) if n else a.group(1), to_dashes(a.group(1))))
    return devices
