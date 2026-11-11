"""Turn a label file (PDF or image) into the 1-bit, head-wide bitmap the M9 prints.

PDFs render through pypdfium2 (a pip wheel), so there's no poppler to install.
"""
from PIL import Image

from .protocol import DPI, HEAD_W, LABEL_W


def _first_page(path):
    """Rasterise a PDF's first page to a grayscale PIL image at the head's DPI."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        page = pdf[0]
        # pdfium renders at 72 dpi for scale 1.
        return page.render(scale=DPI / 72, grayscale=True).to_pil()
    finally:
        pdf.close()


def load_content(path, target_w):
    """Load an image or PDF, scale it to target_w dots wide, dither to 1-bit."""
    img = _first_page(path) if path.lower().endswith(".pdf") else Image.open(path)
    img = img.convert("L")
    h = max(1, round(img.height * target_w / img.width))
    # .convert("1") applies Floyd–Steinberg dithering, which keeps photos legible.
    return img.resize((target_w, h), Image.LANCZOS).convert("1")


def canvas(content, width=HEAD_W, offset=0):
    """Place a 1-bit image on a white, head-wide canvas at x = offset."""
    c = Image.new("1", (width, content.height), 1)        # 1 is white
    c.paste(content, (offset, 0))
    return c


def placement(label_w=LABEL_W, nudge=0):
    """(x offset, clamped?) for a label right-aligned on the head, nudged by dots.

    The strip runs under the right edge of the head, so content is flush right
    and can only move left. A positive nudge is clamped (it would push the label
    off the head); if the left edge still clips, the strip extends past the
    printable area and the fix is a narrower label width, not a nudge.
    """
    want = HEAD_W - label_w + nudge
    offset = max(0, min(want, HEAD_W - label_w))
    return offset, offset != want


def render_label(path, label_w=LABEL_W, nudge=0):
    """Load a label and place it on the head-wide canvas (see placement)."""
    content = load_content(path, label_w)
    return canvas(content, HEAD_W, placement(label_w, nudge)[0])
