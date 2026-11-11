"""Command line: `m9printer label.pdf` prints; `m9printer` alone opens the window."""
import argparse
import sys

from . import __version__, config, printing, transport
from .protocol import HEAT


def main(argv=None):
    s = config.load()
    p = argparse.ArgumentParser(
        prog="m9printer",
        description="Print a 4x6 label to the Milestone M9 over Bluetooth. "
                    "With no file, opens the window.")
    p.add_argument("file", nargs="?", help="label PDF (first page) or image")
    p.add_argument("--addr", default=s["addr"], help=f"printer Bluetooth address (default {s['addr']})")
    p.add_argument("--width-mm", type=float, default=s["width_mm"],
                   help="printed label width in mm (default %(default)s); lower it if the left edge clips")
    p.add_argument("--nudge-mm", type=float, default=s["nudge_mm"],
                   help="move the label left (negative) in mm (default %(default)s)")
    p.add_argument("--density", choices=list(HEAT), default=s["density"])
    p.add_argument("--out", metavar="FILE.bin", help="write the print stream to a file instead of sending")
    p.add_argument("--test", action="store_true", help="check the Bluetooth link (prints nothing)")
    p.add_argument("--list", action="store_true", help="list paired Bluetooth devices")
    p.add_argument("--version", action="version", version=f"m9printer {__version__}")
    a = p.parse_args(argv)

    try:
        if a.list:
            for name, addr in transport.paired_devices() or []:
                print(f"{addr}  {name}")
            return 0
        if a.test:
            printing.send(a.addr, printing.test_stream(a.density))
            print("Link OK.")
            return 0
        if not a.file:
            from .gui import main as gui_main
            return gui_main()
        stream, _, clamped = printing.prepare(a.file, a.width_mm, a.nudge_mm, a.density)
        if clamped:
            print("Note: the label is already flush with the right edge of the head; "
                  "a rightward nudge can't move it further. If the left edge clips, "
                  "lower --width-mm instead.", file=sys.stderr)
        if a.out:
            with open(a.out, "wb") as f:
                f.write(stream)
            print(f"wrote {len(stream)} bytes to {a.out}")
            return 0
        print(f"sending {len(stream)} bytes to {a.addr}…")
        printing.send(a.addr, stream)
        config.save({"addr": a.addr, "width_mm": a.width_mm, "nudge_mm": a.nudge_mm,
                     "density": a.density})
        print("Sent.")
        return 0
    except (transport.TransportError, RuntimeError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
