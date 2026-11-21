#!/usr/bin/env python3
"""Entry for make.fun competition the-poster-for-a-place-that-i-2-20261121-0539.

Writes one travel poster for a place that does not exist to /output/entry.png.

The place is VELMARA, "the isles that drift": floating islands above a calm
sea at golden dawn, a lighthouse on the largest isle, the sun rising behind
them. Drawn procedurally with the standard library only -- no network, no
clock, no randomness, no external files (the sandbox is python:3.13-slim, so
there is no Pillow and no font file to load; the lettering is a small bitmap
font embedded below, rendered at 2x and downsampled for smooth edges).

Deterministic: the same input always produces the same PNG bytes.
Rebuilt in a fresh post-open session so the entry's transcripts cover
every line of this file; the picture itself is unchanged from the draft.
"""

import os
import struct
import zlib
from pathlib import Path

# Output size required by the gate: at most 1024 x 1024, at most 1 MiB.
W = 1024
H = 1024
SS = 2  # supersample factor; the canvas is drawn at 2048 and downsampled
CW = W * SS
CH = H * SS

CREAM = (247, 234, 208)
GOLD = (242, 192, 120)
SUN = (255, 233, 184)
INK = (20, 51, 63)
TEAL_DARK = (15, 46, 61)
TEAL = (27, 69, 80)
TEAL_MID = (42, 90, 102)
RED = (178, 74, 66)

# Sky gradient stops: (fraction of sky height, colour).
SKY = [
    (0.00, (29, 43, 83)),
    (0.30, (91, 74, 125)),
    (0.52, (201, 111, 94)),
    (0.66, (242, 166, 90)),
    (1.00, (247, 200, 116)),
]
SKY_H = 640  # sky occupies the top 640 rows (of 1024)
SEA_TOP = 640


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (
        int(round(lerp(c1[0], c2[0], t))),
        int(round(lerp(c1[1], c2[1], t))),
        int(round(lerp(c1[2], c2[2], t))),
    )


def blend(dst, src, alpha):
    """Alpha-blend src over dst; alpha in [0, 1]."""
    return (
        int(round(src[0] * alpha + dst[0] * (1 - alpha))),
        int(round(src[1] * alpha + dst[1] * (1 - alpha))),
        int(round(src[2] * alpha + dst[2] * (1 - alpha))),
    )


class Canvas:
    """An RGB canvas held as one bytearray, drawn with row spans (fast)."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    def _row(self, y):
        return y * self.w * 3

    def span(self, y, x0, x1, colour):
        """Fill [x0, x1) on row y with a solid colour (clipped)."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w, x1)
        if x1 <= x0:
            return
        r, g, b = colour
        base = self._row(y) + x0 * 3
        n = x1 - x0
        self.buf[base:base + n * 3] = bytes((r, g, b)) * n

    def span_alpha(self, y, x0, x1, colour, alpha):
        """Fill [x0, x1) on row y blending colour over what is there."""
        if y < 0 or y >= self.h or alpha <= 0:
            return
        x0 = max(0, x0)
        x1 = min(self.w, x1)
        if x1 <= x0:
            return
        base = self._row(y) + x0 * 3
        ia = 1.0 - alpha
        for x in range(x0, x1):
            i = base + (x - x0) * 3
            self.buf[i] = int(round(colour[0] * alpha + self.buf[i] * ia))
            self.buf[i + 1] = int(round(colour[1] * alpha + self.buf[i + 1] * ia))
            self.buf[i + 2] = int(round(colour[2] * alpha + self.buf[i + 2] * ia))

    def rect(self, x0, y0, x1, y1, colour):
        for y in range(y0, y1):
            self.span(y, x0, x1, colour)

    def rect_alpha(self, x0, y0, x1, y1, colour, alpha):
        for y in range(y0, y1):
            self.span_alpha(y, x0, x1, colour, alpha)

    def vgrad(self, y0, y1, stops):
        """Vertical gradient between y0 and y1 through (fraction, colour) stops."""
        span_h = y1 - y0
        for y in range(y0, y1):
            t = (y - y0) / max(1, span_h - 1)
            for i in range(len(stops) - 1):
                f0, c0 = stops[i]
                f1, c1 = stops[i + 1]
                if f0 <= t <= f1:
                    self.span(y, 0, self.w, mix(c0, c1, (t - f0) / (f1 - f0)))
                    break
            else:
                self.span(y, 0, self.w, stops[-1][1])

    def circle(self, cx, cy, r, colour, alpha=1.0):
        r2 = r * r
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            dx = int((r2 - dy * dy) ** 0.5)
            if alpha >= 1.0:
                self.span(y, cx - dx, cx + dx + 1, colour)
            else:
                self.span_alpha(y, cx - dx, cx + dx + 1, colour, alpha)

    def ellipse(self, cx, cy, rx, ry, colour, alpha=1.0):
        for y in range(cy - ry, cy + ry + 1):
            dy = (y - cy) / ry
            dx = int(rx * (max(0.0, 1.0 - dy * dy)) ** 0.5)
            if alpha >= 1.0:
                self.span(y, cx - dx, cx + dx + 1, colour)
            else:
                self.span_alpha(y, cx - dx, cx + dx + 1, colour, alpha)

    def polygon(self, points, colour, alpha=1.0):
        """Scanline-fill a polygon given as [(x, y), ...]."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        y0, y1 = min(ys), max(ys)
        n = len(points)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, ya = points[i]
                x1, yb = points[(i + 1) % n]
                if ya == yb:
                    continue
                if (ya <= y < yb) or (yb <= y < ya):
                    xs.append(x0 + (y - ya) * (x1 - x0) / (yb - ya))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                if alpha >= 1.0:
                    self.span(y, int(xs[i]), int(xs[i + 1]) + 1, colour)
                else:
                    self.span_alpha(y, int(xs[i]), int(xs[i + 1]) + 1, colour, alpha)

    def thick_line(self, x0, y0, x1, y1, width, colour):
        """A line drawn as a thin polygon (for birds and rays)."""
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        self.polygon(
            [
                (int(x0 + nx), int(y0 + ny)),
                (int(x1 + nx), int(y1 + ny)),
                (int(x1 - nx), int(y1 - ny)),
                (int(x0 - nx), int(y0 - ny)),
            ],
            colour,
        )


# 5x7 bitmap font, only the letters the poster uses.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "V": ("10001", "10001", "10001", "01010", "01010", "00100", "00100"),
}


def text_width(text, scale, spacing):
    w = 0
    for ch in text:
        w += 0 if ch == " " else 5 * scale
        w += spacing
    return w - spacing if text else 0


def draw_text(cv, text, cx, y, scale, colour, spacing):
    """Draw centred text with its baseline-top at y (canvas coordinates)."""
    total = text_width(text, scale, spacing)
    x = cx - total // 2
    for ch in text:
        if ch != " ":
            glyph = FONT[ch]
            for row_i, row in enumerate(glyph):
                for col_i, bit in enumerate(row):
                    if bit == "1":
                        cv.rect(
                            x + col_i * scale,
                            y + row_i * scale,
                            x + (col_i + 1) * scale,
                            y + (row_i + 1) * scale,
                            colour,
                        )
        x += (5 * scale if ch != " " else 5 * scale) + spacing


def draw_poster(cv):
    s = SS  # all coordinates below are in 1024-space, scaled by s
    cx = 512 * s

    # --- sky ---
    cv.vgrad(0, SKY_H * s, SKY)

    # --- sun: halo rings, then the disc, low over the horizon ---
    sun_cx, sun_cy, sun_r = 512 * s, 468 * s, 108 * s
    cv.circle(sun_cx, sun_cy, int(sun_r * 1.55), (247, 200, 116), alpha=0.25)
    cv.circle(sun_cx, sun_cy, int(sun_r * 1.25), (247, 200, 116), alpha=0.35)
    cv.circle(sun_cx, sun_cy, sun_r, SUN)

    # --- high clouds: soft pale bands ---
    for (ccx, ccy, rx, ry, a) in [
        (300, 250, 190, 16, 0.35),
        (760, 210, 220, 14, 0.30),
        (180, 330, 150, 12, 0.28),
        (860, 330, 170, 13, 0.30),
    ]:
        cv.ellipse(ccx * s, ccy * s, rx * s, ry * s, (247, 214, 168), alpha=a)

    # --- birds ---
    for (bx, by, bs) in [(120, 300, 16), (170, 282, 12), (880, 290, 14), (930, 312, 11)]:
        bx, by, bs = bx * s, by * s, bs * s
        cv.thick_line(bx - bs, by, bx, by + bs // 2, 3 * s, INK)
        cv.thick_line(bx, by + bs // 2, bx + bs, by, 3 * s, INK)

    # --- far isle (pale, atmospheric), left ---
    cv.polygon(
        [
            (60 * s, 560 * s), (330 * s, 560 * s), (300 * s, 596 * s),
            (262 * s, 640 * s), (210 * s, 668 * s), (150 * s, 640 * s),
            (104 * s, 600 * s),
        ],
        TEAL_MID,
    )

    # --- main isle, centre-right, with the lighthouse ---
    isle = [
        (380 * s, 520 * s), (760 * s, 520 * s), (742 * s, 556 * s),
        (700 * s, 592 * s), (640 * s, 640 * s), (590 * s, 668 * s),
        (540 * s, 640 * s), (470 * s, 600 * s), (410 * s, 556 * s),
    ]
    cv.polygon(isle, INK)
    # grassy top rim in warm gold light
    cv.polygon(
        [(380 * s, 520 * s), (760 * s, 520 * s), (752 * s, 532 * s), (392 * s, 532 * s)],
        (216, 164, 92),
    )
    # waterfalls pouring off the isle's edges into the mist
    for (wx, wlen) in [(430, 96), (700, 120)]:
        for k in range(3):
            cv.rect_alpha(
                (wx + k * 7) * s, 560 * s, (wx + k * 7 + 3) * s,
                (560 + wlen - k * 18) * s, (247, 234, 208), 0.55 - k * 0.12,
            )
    # lighthouse on the main isle
    lx = 560 * s
    cv.polygon(
        [(lx - 16 * s, 520 * s), (lx + 16 * s, 520 * s),
         (lx + 11 * s, 436 * s), (lx - 11 * s, 436 * s)],
        CREAM,
    )
    cv.rect(lx - 13 * s, 488 * s, lx + 13 * s, 496 * s, RED)
    cv.rect(lx - 12 * s, 460 * s, lx + 12 * s, 468 * s, RED)
    cv.rect(lx - 14 * s, 436 * s, lx + 14 * s, 428 * s, RED)
    cv.rect(lx - 9 * s, 420 * s, lx + 9 * s, 428 * s, (255, 240, 170))
    cv.polygon(
        [(lx - 12 * s, 420 * s), (lx + 12 * s, 420 * s), (lx, 406 * s)],
        RED,
    )
    # light beams sweeping from the lamp room
    cv.polygon(
        [(lx - 8 * s, 424 * s), (300 * s, 392 * s), (300 * s, 440 * s), (lx - 8 * s, 430 * s)],
        (255, 240, 170), alpha=0.20,
    )
    cv.polygon(
        [(lx + 8 * s, 424 * s), (830 * s, 396 * s), (830 * s, 442 * s), (lx + 8 * s, 430 * s)],
        (255, 240, 170), alpha=0.20,
    )

    # --- small isle, right, lower ---
    cv.polygon(
        [
            (800 * s, 600 * s), (960 * s, 600 * s), (940 * s, 628 * s),
            (906 * s, 656 * s), (868 * s, 676 * s), (836 * s, 652 * s),
            (812 * s, 624 * s),
        ],
        TEAL,
    )

    # --- mist band where the isles meet the sea ---
    cv.rect_alpha(0, 636 * s, CW, 668 * s, (247, 214, 168), 0.30)

    # --- sea ---
    sea_stops = [(0.0, (42, 107, 116)), (0.45, (27, 79, 92)), (1.0, TEAL_DARK)]
    cv.vgrad(SEA_TOP * s, CH, sea_stops)
    # sun reflection: a column of gold dashes under the sun
    for i in range(26):
        y = (672 + i * 13) * s
        half = (26 + i * 7) * s
        a = 0.55 - i * 0.018
        cv.rect_alpha(cx - half, y, cx + half, y + 4 * s, GOLD, max(0.06, a))
    # long calm wave lines
    for (wy, wl, a) in [(720, 200, 0.25), (800, 260, 0.20), (900, 320, 0.16), (980, 380, 0.12)]:
        y = wy * s
        cv.rect_alpha(cx - wl * s, y, cx + wl * s, y + 3 * s, (247, 234, 208), a)
        cv.rect_alpha(cx - wl * s // 2, y + 26 * s, cx + wl * s // 2, y + 29 * s,
                      (247, 234, 208), a * 0.7)

    # --- frame: double cream rule ---
    cv.rect(0, 0, CW, 10 * s, CREAM)
    cv.rect(0, CH - 10 * s, CW, CH, CREAM)
    cv.rect(0, 0, 10 * s, CH, CREAM)
    cv.rect(CW - 10 * s, 0, CW, CH, CREAM)
    cv.rect(22 * s, 22 * s, CW - 22 * s, 24 * s, CREAM)
    cv.rect(22 * s, CH - 24 * s, CW - 22 * s, CH - 22 * s, CREAM)
    cv.rect(22 * s, 22 * s, 24 * s, CH - 22 * s, CREAM)
    cv.rect(CW - 24 * s, 22 * s, CW - 22 * s, CH - 22 * s, CREAM)

    # --- type: the place name, then the one-line promise ---
    draw_text(cv, "VELMARA", cx, 96 * s, 15 * s, CREAM, 16 * s)
    draw_text(cv, "THE ISLES THAT DRIFT", cx, 218 * s, 5 * s, GOLD, 7 * s)


def downsample(src, w, h):
    """Average each 2x2 block of the supersampled canvas to the final size."""
    out = bytearray(w * h * 3)
    sw = w * SS
    for y in range(h):
        sy = y * SS
        for x in range(w):
            sx = x * SS
            o = (y * w + x) * 3
            for c in range(3):
                i00 = (sy * sw + sx) * 3 + c
                i01 = i00 + 3
                i10 = (sy * sw + sw + sx) * 3 + c
                i11 = i10 + 3
                out[o + c] = (src[i00] + src[i01] + src[i10] + src[i11] + 2) // 4
    return bytes(out)


def encode_png(rgb, w, h):
    """Encode RGB bytes as a PNG (filter 0 per row, zlib level 9)."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def main():
    cv = Canvas(CW, CH)
    draw_poster(cv)
    rgb = downsample(cv.buf, W, H)
    png = encode_png(rgb, W, H)
    out_dir = Path(os.environ.get("OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "entry.png").write_bytes(png)


if __name__ == "__main__":
    main()
