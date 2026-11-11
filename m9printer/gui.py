"""The window: pick a label, see where it lands on the A4 sheet, print it."""
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from . import __version__, config, printing, transport
from .protocol import HEAD_W, HEAT, build
from .render import load_content, placement

ADDR_RE = re.compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}")
PREVIEW_W = 280                                     # the A4 sheet, scaled
PAGE_H = round(printing.mm_to_dots(printing.A4_H_MM) * PREVIEW_W / HEAD_W)
FILETYPES = [("Labels", "*.pdf *.png *.jpg *.jpeg *.gif *.bmp *.tif *.tiff *.webp"),
             ("All files", "*.*")]
DENSITY_NAMES = {"low": "Light", "normal": "Normal", "thick": "Dark"}
FEED_NAMES = {"label": "One label", "sheet": "Full A4 sheet"}
ACCENT = "#3a58d4"
SHEET = "#d9d9e1"       # the part of the sheet that stays blank
UNFED = "#f3f3f6"       # paper the printer won't feed in one-label mode


class App:
    def __init__(self, root, path=None):
        self.root = root
        self.s = config.load()
        self.path = None
        self._cache = (None, None)      # ((path, width dots), loaded 1-bit content)
        self._pending = None            # debounced preview job
        self._generation = 0            # drops preview results that a newer change overtook
        self._last = None               # last preview result, redrawn when only the feed changes
        self._photo = None
        root.title("M9 Label Printer")
        self._build()
        self.refresh_devices()
        if path:
            self.set_file(path)

    # ---- layout -------------------------------------------------------------
    def _build(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        f = ttk.Frame(outer)                     # controls, left
        f.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        f.columnconfigure(1, weight=1)

        def row(r, text):
            ttk.Label(f, text=text).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 10))

        row(0, "Label")
        self.file_var = tk.StringVar(value="No file chosen")
        ttk.Label(f, textvariable=self.file_var, foreground="#555", width=22).grid(
            row=0, column=1, sticky="ew")
        ttk.Button(f, text="Choose…", command=self.choose).grid(row=0, column=2, sticky="e")

        row(1, "Printer")
        self.addr_var = tk.StringVar(value=self.s["addr"])
        self.addr_box = ttk.Combobox(f, textvariable=self.addr_var, values=[], width=24)
        self.addr_box.grid(row=1, column=1, sticky="ew")
        ttk.Button(f, text="Refresh", command=self.refresh_devices).grid(row=1, column=2, sticky="e")

        row(2, "Width (mm)")
        self.width_var = tk.StringVar(value=f"{self.s['width_mm']:g}")
        ttk.Spinbox(f, from_=40, to=110, increment=0.5, width=8, textvariable=self.width_var,
                    command=self.schedule_preview).grid(row=2, column=1, sticky="w")

        row(3, "Nudge (mm)")
        self.nudge_var = tk.StringVar(value=f"{self.s['nudge_mm']:g}")
        ttk.Spinbox(f, from_=-100, to=10, increment=0.5, width=8, textvariable=self.nudge_var,
                    command=self.schedule_preview).grid(row=3, column=1, sticky="w")
        ttk.Label(f, text="Negative moves the label left.", foreground="#777").grid(
            row=4, column=1, columnspan=2, sticky="w")

        row(5, "Darkness")
        self.density_var = tk.StringVar(value=self.s["density"])
        dens = ttk.Frame(f)
        dens.grid(row=5, column=1, columnspan=2, sticky="w")
        for key in HEAT:
            ttk.Radiobutton(dens, text=DENSITY_NAMES[key], value=key,
                            variable=self.density_var).pack(side="left", padx=(0, 10))

        row(6, "Paper feed")
        self.feed_var = tk.StringVar(value=self.s["feed"])
        feed = ttk.Frame(f)
        feed.grid(row=6, column=1, columnspan=2, sticky="w")
        for key, name in FEED_NAMES.items():
            ttk.Radiobutton(feed, text=name, value=key, variable=self.feed_var,
                            command=self._redraw).pack(side="left", padx=(0, 10))

        for v in (self.width_var, self.nudge_var):
            v.trace_add("write", lambda *_: self.schedule_preview())

        buttons = ttk.Frame(f)
        buttons.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(18, 8))
        self.test_btn = ttk.Button(buttons, text="Test connection", command=self.test)
        self.test_btn.pack(side="left")
        # A native default button: macOS paints it in the system accent colour (Aqua
        # ignores custom button colours), other platforms give it the default ring.
        self.print_btn = ttk.Button(buttons, text="Print", command=self.print_label,
                                    default="active", width=12)
        self.print_btn.pack(side="right")
        self.root.bind("<Return>", lambda _: self.print_label())

        self.status = tk.StringVar(value="Choose a label to start.")
        ttk.Label(f, textvariable=self.status, wraplength=330, justify="left").grid(
            row=8, column=0, columnspan=3, sticky="nw")
        f.rowconfigure(9, weight=1)
        ttk.Label(f, text=f"v{__version__}", foreground="#aaa").grid(row=10, column=0, sticky="sw")

        side = ttk.Frame(outer)                  # preview, right
        side.grid(row=0, column=1, sticky="n")
        self.preview = tk.Canvas(side, width=PREVIEW_W, height=PAGE_H, bg=SHEET,
                                 highlightthickness=1, highlightbackground="#b8b8c4")
        self.preview.pack()
        ttk.Label(side, text="The A4 sheet; your label is in the blue box.",
                  foreground="#777").pack(anchor="w", pady=(6, 0))
        self._draw_empty()

    # ---- inputs -------------------------------------------------------------
    def _numbers(self):
        """(width mm, nudge mm) or None while a field holds something that isn't a number."""
        try:
            w, n = float(self.width_var.get()), float(self.nudge_var.get())
        except ValueError:
            return None
        return (w, n) if 20 <= w <= 210 else None

    def _addr(self):
        m = ADDR_RE.search(self.addr_var.get())
        return m.group(0) if m else None

    def choose(self):
        path = filedialog.askopenfilename(title="Choose a label", filetypes=FILETYPES)
        if path:
            self.set_file(path)

    def set_file(self, path):
        self.path = path
        self.file_var.set(path.replace("\\", "/").rsplit("/", 1)[-1])
        self.status.set("Loading…")
        self.schedule_preview(0)

    def refresh_devices(self):
        def work():
            devices = transport.paired_devices()
            self.root.after(0, lambda: self._set_devices(devices))
        threading.Thread(target=work, daemon=True).start()

    def _set_devices(self, devices):
        current = (self._addr() or "").replace("-", ":").upper()
        labels = [f"{name}  ({addr})" for name, addr in devices]
        self.addr_box["values"] = labels
        for label, (_, addr) in zip(labels, devices):
            if addr.replace("-", ":").upper() == current:
                self.addr_var.set(label)

    # ---- preview ------------------------------------------------------------
    def schedule_preview(self, delay=250):
        if self._pending:
            self.root.after_cancel(self._pending)
        self._pending = self.root.after(delay, self._start_preview)

    def _content(self, width_mm):
        """The loaded label at this width, reusing the last load when only the nudge changed."""
        key = (self.path, printing.mm_to_dots(width_mm))
        if self._cache[0] != key:
            self._cache = (key, load_content(self.path, key[1]))
        return self._cache[1]

    def _start_preview(self):
        self._pending = None
        nums = self._numbers()
        if not self.path or not nums:
            return
        self._generation += 1
        gen = self._generation

        def work():
            try:
                content = self._content(nums[0])
                offset, clamped = placement(content.width, printing.mm_to_dots(nums[1]))
                result = (content, offset, clamped, None)
            except Exception as e:     # a broken file shouldn't take the window down
                result = (None, 0, False, e)
            self.root.after(0, lambda: self._show_preview(gen, *result))
        threading.Thread(target=work, daemon=True).start()

    def _draw_empty(self):
        c = self.preview
        c.delete("all")
        c.create_text(PREVIEW_W // 2, PAGE_H // 2, text="Preview appears here", fill="#888")

    def _show_preview(self, gen, content, offset, clamped, error):
        if gen != self._generation:
            return
        if error:
            self._last = None
            self._draw_empty()
            self.status.set(f"Couldn't read that file: {error}")
            return
        self._last = (content, offset)
        self._redraw()
        self.status.set(
            "The label is flush with the right edge of the head and can't move further right. "
            "If its left edge clips, lower the width instead." if clamped else
            "Ready. Load the label strip, then Print.")

    def _redraw(self):
        """Draw the A4 sheet, the label in its corner, and where the paper stops."""
        if not self._last:
            return
        content, offset = self._last
        scale = PREVIEW_W / HEAD_W
        x0, w = round(offset * scale), max(1, round(content.width * scale))
        h = max(1, round(content.height * scale))
        self._photo = ImageTk.PhotoImage(content.convert("L").resize((w, h), Image.BOX))
        c = self.preview
        c.delete("all")
        if self.feed_var.get() == "label":
            # Only the label's length of paper comes out; the rest of the sheet doesn't.
            c.create_rectangle(0, h, PREVIEW_W, PAGE_H, fill=UNFED, width=0)
            c.create_line(0, h, PREVIEW_W, h, fill=ACCENT, dash=(4, 3))
            c.create_text(PREVIEW_W // 2, h + 14, text="paper stops here", fill=ACCENT)
        else:
            c.create_text(PREVIEW_W // 2, PAGE_H - 14, text="feeds the full A4 sheet",
                          fill="#666")
        c.create_image(x0, 0, image=self._photo, anchor="nw")
        c.create_rectangle(x0, 0, x0 + w - 1, h - 1, outline=ACCENT, width=2)

    # ---- actions ------------------------------------------------------------
    def _busy(self, on, message=None):
        state = "disabled" if on else "normal"
        self.print_btn.configure(state=state)
        self.test_btn.configure(state=state)
        if message:
            self.status.set(message)

    def _log(self, line):
        self.root.after(0, lambda: self.status.set(line))

    def _run(self, job, done_message):
        addr = self._addr()
        if not addr:
            self.status.set("Pick the printer, or type its Bluetooth address (like 41-42-86-99-1A-7E).")
            return
        self._busy(True, "Connecting…")

        def work():
            try:
                job(addr)
                msg = done_message
            except Exception as e:
                msg = str(e)
            self.root.after(0, lambda: (self._busy(False), self.status.set(msg)))
        threading.Thread(target=work, daemon=True).start()

    def test(self):
        density = self.density_var.get()
        self._run(lambda addr: printing.send(addr, printing.test_stream(density), log=self._log),
                  "Connected — the printer is reachable.")

    def print_label(self):
        nums = self._numbers()
        if not self.path:
            self.status.set("Choose a label first.")
            return
        if not nums:
            self.status.set("Width and nudge need to be numbers (width between 20 and 210 mm).")
            return
        density, feed = self.density_var.get(), self.feed_var.get()

        def job(addr):
            img, _ = printing.compose(self._content(nums[0]), nums[1])
            stream = build(img, density, feed)
            self._log(f"Sending {len(stream) // 1024} KB…")
            printing.send(addr, stream, log=lambda _: None)
            config.save({"addr": addr, "width_mm": nums[0], "nudge_mm": nums[1],
                         "density": density, "feed": feed})
        self._run(job, "Sent. The label should be printing.")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = tk.Tk()
    app = App(root, path=argv[0] if argv else None)
    if sys.platform == "darwin":
        # Files dropped on the app icon or opened with "Open With" arrive as an Apple Event.
        root.createcommand("::tk::mac::OpenDocument", lambda *paths: paths and app.set_file(paths[0]))
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
