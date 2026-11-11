# M9 Label Printer

Print full-width 4×6 in shipping labels on the **Milestone / Meihengtong M9**
(the A4 thermal printer) straight from your computer over Bluetooth — no phone,
no vendor app. Pick a label (PDF or image), check where it lands, press Print.

| Platform | Status |
|---|---|
| macOS (Apple silicon) | Tested on real hardware |
| Windows 10/11 | Built and unit-tested in CI; not yet tried on a real printer |
| Linux (x64, glibc 2.35+) | Built and unit-tested in CI; not yet tried on a real printer |

## Install

Download the file for your system from the
[latest release](../../releases/latest).

**macOS** — unzip `M9-Label-Printer-macOS-arm64.zip` and drag
**M9 Label Printer** to Applications. The app isn't notarised by Apple, so the
first time, right-click it → **Open** → **Open** (or run
`xattr -dr com.apple.quarantine "/Applications/M9 Label Printer.app"`).
Allow Bluetooth access when macOS asks.

**Windows** — run `M9-Label-Printer-Windows-x64.exe`. SmartScreen may warn
about an unknown publisher: **More info** → **Run anyway**.

**Linux** — `tar xzf M9-Label-Printer-Linux-x64.tar.gz && ./m9-label-printer`.
Needs BlueZ (standard on desktop distros).

## Use

1. Pair the printer once in your system's Bluetooth settings (it shows up as
   **M9**). Disconnect it from your phone — it takes one connection at a time.
2. Open the app, **Choose…** a label. A PDF prints its first page.
3. Pick the printer (paired devices are listed; you can also type its address,
   like `41-42-86-99-1A-7E`). **Test connection** checks the link without
   printing anything.
4. Load the label strip under the right side of the print head and **Print**.

The preview shows the whole A4 print head in grey and your label in the blue box.

### Getting the placement right

The strip runs under the **right edge** of the head, so the label is printed
flush right and can only move left.

- **Clipped on the right** → set a negative **Nudge** (moves it left).
- **Clipped on the left** → lower the **Width** a little (e.g. 101.6 → 99). The
  strip sits partly past the printable edge, so a narrower label is the fix; a
  rightward nudge can't help, and the app says so.
- **Too light / too dark** → change **Darkness**.

Settings are remembered between runs.

## Command line

```bash
pip install .                 # from a clone; needs pbmtojbg on PATH (brew/apt install jbigkit)
m9printer label.pdf           # print with the saved settings
m9printer label.pdf --width-mm 99 --nudge-mm -2 --density thick
m9printer --list              # paired Bluetooth devices
m9printer --test              # check the link, print nothing
m9printer label.pdf --out job.bin   # write the print stream instead of sending
m9printer                     # no file: opens the window
```

## How it works

The M9's USB port only speaks basic ESC/POS raster, capped at about 48 mm wide —
too narrow for a 4 in label. Its full-width protocol is **Bluetooth only**,
reverse-engineered from the `com.mht.docprinter` Android app:

```
settings   1F FD 01 <code> <value> …        (code 08 = heat: 130 / 160 / 190)
per band   1F 01 05 LE16(bytes/row) LE16(rows) LE16(length) <JBIG1 BIE>
end        0A 0A 0A 1F 01 06
```

- Bitmap: 1 = black, MSB first, Floyd–Steinberg dithered; head width 1680 dots
  (A4 at 203 dpi); a 4 in label is 812 dots, right-aligned; bands of 100 rows.
- JBIG1 is jbigkit with default options, single layer (`pbmtojbg -q`) — the same
  library the app bundles, confirmed by decompiling its `libSerialPort.so`.
- Sent over RFCOMM channel 1. Windows and Linux use Python's own Bluetooth
  sockets. macOS Python has none, and the `/dev/cu.M9` serial port macOS creates
  doesn't carry data to this printer, so a small IOBluetooth helper
  (`helpers/btsend2.swift`) opens the channel asynchronously and writes it.

### Layout

```
m9printer/
  protocol.py   print stream: settings, packing, JBIG bands
  render.py     PDF (pypdfium2) / image → 1-bit head-wide bitmap, placement
  printing.py   one job: render → encode → send
  transport/    Bluetooth per OS: macos.py, windows.py, linux.py
  gui.py        the window (Tkinter)
  cli.py        the command line
helpers/btsend2.swift   macOS RFCOMM helper
m9printer.spec          PyInstaller build for all platforms
```

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install pillow pypdfium2 pyinstaller
mkdir -p m9printer/bin
# macOS: helper + tools into m9printer/bin (CI builds pbmtojbg from source instead)
swiftc -O -o m9printer/bin/btsend2 helpers/btsend2.swift
brew install jbigkit blueutil
cp "$(brew --prefix jbigkit)/bin/pbmtojbg" "$(brew --prefix blueutil)/bin/blueutil" m9printer/bin/
.venv/bin/python -m unittest discover -s tests   # tests
.venv/bin/python -m m9printer                    # run the window
.venv/bin/pyinstaller m9printer.spec             # build the app into dist/
```

Tkinter needs a Python built with Tk (on Homebrew: `brew install python-tk@3.13`).

### Releasing

Bump `__version__` in `m9printer/__init__.py`, commit, then tag and push:

```bash
git tag v0.1.1 && git push origin v0.1.1
```

GitHub Actions builds all three platforms (compiling `pbmtojbg` from the
checksum-pinned jbigkit source), runs the tests on each — including a
golden-bytes check of the encoder — and publishes the release.

Bundled third-party programs and their licences are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
