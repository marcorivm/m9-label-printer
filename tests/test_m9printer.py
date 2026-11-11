"""Unit tests. Run: python -m unittest discover -s tests"""
import random
import struct
import unittest

from PIL import Image

from m9printer import printing, transport
from m9printer.protocol import BAND_ROWS, DENSITY, HEAD_W, LABEL_W, build, pack_1bpp
from m9printer.render import canvas, placement
from m9printer.resources import find_binary


def reference_pack(img):
    """The original per-pixel packer from m9gen.py, kept as the spec."""
    w, h = img.size
    px = img.load()
    bpl = (w + 7) // 8
    out = bytearray(bpl * h)
    for y in range(h):
        for x in range(w):
            if px[x, y] == 0:
                out[y * bpl + (x >> 3)] |= 0x80 >> (x & 7)
    return bpl, bytes(out)


def noise(w, h, seed=1):
    rnd = random.Random(seed)
    img = Image.new("1", (w, h), 1)
    px = img.load()
    for y in range(h):
        for x in range(w):
            if rnd.random() < 0.3:
                px[x, y] = 0
    return img


class Packing(unittest.TestCase):
    def test_matches_reference_on_byte_aligned_width(self):
        img = noise(64, 9)
        self.assertEqual(pack_1bpp(img), reference_pack(img))

    def test_matches_reference_with_row_padding(self):
        for w in (1, 7, 13, 30):
            img = noise(w, 5, seed=w)
            self.assertEqual(pack_1bpp(img), reference_pack(img), f"width {w}")

    def test_black_is_one(self):
        self.assertEqual(pack_1bpp(Image.new("1", (8, 1), 0)), (1, b"\xff"))
        self.assertEqual(pack_1bpp(Image.new("1", (8, 1), 1)), (1, b"\x00"))


class Placement(unittest.TestCase):
    def test_flush_right_by_default(self):
        self.assertEqual(placement(LABEL_W, 0), (HEAD_W - LABEL_W, False))

    def test_negative_nudge_moves_left(self):
        self.assertEqual(placement(LABEL_W, -40), (HEAD_W - LABEL_W - 40, False))

    def test_positive_nudge_is_clamped_and_reported(self):
        self.assertEqual(placement(LABEL_W, 28), (HEAD_W - LABEL_W, True))

    def test_cannot_go_past_left_edge(self):
        self.assertEqual(placement(LABEL_W, -5000), (0, True))

    def test_mm_to_dots(self):
        self.assertEqual(printing.mm_to_dots(101.6), LABEL_W)
        self.assertEqual(printing.mm_to_dots(25.4), 203)


class Addresses(unittest.TestCase):
    def test_normalises_both_ways(self):
        self.assertEqual(transport.to_colons("41-42-86-99-1a-7e"), "41:42:86:99:1A:7E")
        self.assertEqual(transport.to_dashes(" 41:42:86:99:1a:7e"), "41-42-86-99-1A-7E")


class Density(unittest.TestCase):
    def test_heat_byte_is_last(self):
        self.assertEqual(DENSITY["normal"][-5:], bytes([0x1F, 0xFD, 1, 8, 160]))
        self.assertEqual(DENSITY["low"][-1], 130)
        self.assertEqual(DENSITY["thick"][-1], 190)

    def test_matches_original_normal_preamble(self):
        original = bytes([0x1F, 0xFD, 1, 1, 0x10, 0x1F, 0xFD, 1, 2, 0x64, 0x1F, 0xFD, 1, 3, 1,
                          0x1F, 0xFD, 1, 4, 2, 0x1F, 0xFD, 1, 5, 0, 0x1F, 0xFD, 1, 8, 160])
        self.assertEqual(DENSITY["normal"], original)

    def test_connection_test_sends_no_raster(self):
        stream = printing.test_stream()
        self.assertNotIn(b"\x1f\x01\x05", stream)
        self.assertNotIn(b"\x1f\x01\x06", stream)


@unittest.skipUnless(find_binary("pbmtojbg", "M9_PBMTOJBG"), "pbmtojbg not installed")
class Stream(unittest.TestCase):
    def test_structure(self):
        content = noise(LABEL_W, BAND_ROWS * 2 + 17, seed=3)
        img = canvas(content, offset=HEAD_W - LABEL_W)
        stream = build(img)
        self.assertTrue(stream.startswith(DENSITY["normal"]))
        self.assertTrue(stream.endswith(b"\x0a\x0a\x0a\x1f\x01\x06"))
        # Walk the bands: header, then exactly len bytes of BIE each.
        pos, rows_seen = len(DENSITY["normal"]), []
        while stream[pos:pos + 3] == b"\x1f\x01\x05":
            bpl, rows, n = struct.unpack("<HHH", stream[pos + 3:pos + 9])
            self.assertEqual(bpl, HEAD_W // 8)
            rows_seen.append(rows)
            pos += 9 + n
        self.assertEqual(rows_seen, [BAND_ROWS, BAND_ROWS, 17])
        self.assertEqual(stream[pos:], b"\x0a\x0a\x0a\x1f\x01\x06")

    def test_golden_bytes(self):
        """Exactly the stream the jbigkit 2.2 build that printed real labels produces.
        Guards each platform's pbmtojbg build (CI compiles it from source)."""
        import hashlib
        img = canvas(noise(LABEL_W, 237, seed=7), offset=HEAD_W - LABEL_W)
        stream = build(img)
        self.assertEqual(len(stream), 24204)
        self.assertEqual(hashlib.sha256(stream).hexdigest(),
                         "162e0e57a78d8f32c31bcede12e43e323cbc36c4120a23a7a340371124a9f766")


if __name__ == "__main__":
    unittest.main()
