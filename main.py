#!/usr/bin/env python3
"""VELMARA - The Isles That Drift.

A travel poster for a place that does not exist, drawn entirely with the
Python standard library. No image files, no network, no clock, no random
numbers: the same run always writes the same bytes.

Scene: a golden dawn over a calm sea. Three islands drift above the
horizon; the largest carries a lighthouse whose beam sweeps the morning
sky. The sun's reflection runs down the water toward the viewer, and the
name of the place stands large across the top of the sky.

Run:  python3 main.py          (writes $OUTPUT_DIR/entry.png, default /output)
"""

import os
import struct
import zlib

W = 1024
H = 1024
HORIZON = 640  # where the sea begins


# ---------------------------------------------------------------- palette

def lerp(a, b, t):
    return int(round(a + (b - a) * t))


def mix(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


SKY_STOPS = [
    (0.00, (24, 22, 72)),     # indigo night, top of the poster
    (0.28, (74, 44, 118)),    # violet
    (0.55, (172, 74, 104)),   # rose
    (0.78, (238, 128, 62)),   # orange dawn
    (1.00, (250, 196, 96)),   # gold at the horizon
]

SEA_STOPS = [
    (0.00, (22, 84, 102)),    # sunlit teal at the horizon
    (0.45, (14, 62, 84)),     # deep teal
    (1.00, (8, 34, 56)),      # dark water at the bottom
]

CREAM = (255, 242, 210)
GOLD = (238, 192, 104)
SUN_CORE = (255, 238, 186)
SUN_HALO = (255, 196, 110)
ROCK = (96, 74, 58)
ROCK_DARK = (58, 44, 38)
GRASS = (86, 148, 88)
GRASS_DARK = (54, 106, 66)
TOWER = (250, 244, 230)
BAND = (196, 64, 52)
LAMP = (255, 214, 120)


def sky_at(y):
    t = y / (HORIZON - 1)
    for i in range(len(SKY_STOPS) - 1):
        t0, c0 = SKY_STOPS[i]
        t1, c1 = SKY_STOPS[i + 1]
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0))
    return SKY_STOPS[-1][1]


def sea_at(y):
    t = (y - HORIZON) / (H - 1 - HORIZON)
    for i in range(len(SEA_STOPS) - 1):
        t0, c0 = SEA_STOPS[i]
        t1, c1 = SEA_STOPS[i + 1]
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0))
    return SEA_STOPS[-1][1]


# ---------------------------------------------------------------- canvas

buf = bytearray(W * H * 3)


def span(y, x0, x1, color):
    """Fill one horizontal run of pixels on row y with a solid color."""
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    row = y * W * 3
    run = bytes(color) * (x1 - x0 + 1)
    buf[row + x0 * 3: row + (x1 + 1) * 3] = run


def blend_span(y, x0, x1, color, alpha):
    """Blend a horizontal run over what is already there (alpha 0..1)."""
    if y < 0 or y >= H or alpha <= 0.0:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    row = y * W * 3
    for x in range(x0, x1 + 1):
        i = row + x * 3
        buf[i] = lerp(buf[i], color[0], alpha)
        buf[i + 1] = lerp(buf[i + 1], color[1], alpha)
        buf[i + 2] = lerp(buf[i + 2], color[2], alpha)


def ellipse(cx, cy, rx, ry, color, alpha=1.0):
    """Filled ellipse, optionally translucent."""
    for dy in range(-ry, ry + 1):
        y = cy + dy
        if y < 0 or y >= H:
            continue
        f = 1.0 - (dy / ry) ** 2
        if f < 0:
            continue
        dx = int(rx * (f ** 0.5))
        if alpha >= 1.0:
            span(y, cx - dx, cx + dx, color)
        else:
            blend_span(y, cx - dx, cx + dx, color, alpha)


def disc(cx, cy, r, color, alpha=1.0):
    ellipse(cx, cy, r, r, color, alpha)


def tapered_rock(cx, top_y, half_top, tip_y, color_top, color_tip):
    """An island's underside: a cliff that narrows to a point below."""
    height = tip_y - top_y
    for k in range(height + 1):
        y = top_y + k
        t = k / height
        half = int(half_top * (1.0 - t) + 0.5)
        span(y, cx - half, cx + half, mix(color_top, color_tip, t))


def beam(x0, y0, x1, y1, color, alpha):
    """A soft light beam: a widening triangle from (x0, y0) to (x1, y1)."""
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for s in range(steps + 1):
        t = s / steps
        x = int(x0 + (x1 - x0) * t)
        y = int(y0 + (y1 - y0) * t)
        half = int(2 + 26 * t)
        blend_span(y, x - half, x + half, color, alpha * (1.0 - 0.55 * t))


# ---------------------------------------------------------------- 5x7 font

# Only the letters the poster actually prints. Each glyph is 7 rows of
# 5 bits, '1' meaning ink.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
}


def text_width(text, scale, gap):
    return len(text) * (5 * scale + gap) - gap


def draw_text(text, x0, y0, scale, color, shadow=None):
    """Draw text left-aligned at (x0, y0); glyphs are scale x scale blocks."""
    x = x0
    gap = scale
    for ch in text:
        glyph = GLYPHS.get(ch)
        if glyph is None:
            x += 5 * scale + gap
            continue
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                px = x + gx * scale
                py = y0 + gy * scale
                if shadow is not None:
                    for sy in range(py + 2, py + 2 + scale):
                        span(sy, px + 2, px + 2 + scale - 1, shadow)
                for sy in range(py, py + scale):
                    span(sy, px, px + scale - 1, color)
        x += 5 * scale + gap


def draw_text_centered(text, y0, scale, color, shadow=None):
    w = text_width(text, scale, scale)
    draw_text(text, (W - w) // 2, y0, scale, color, shadow)


# ---------------------------------------------------------------- scene

def paint_sky():
    for y in range(HORIZON):
        span(y, 0, W - 1, sky_at(y))


def paint_sun():
    # Wide halo first, then the disc itself, so the core stays brightest.
    disc(716, 292, 168, SUN_HALO, 0.20)
    disc(716, 292, 128, SUN_HALO, 0.28)
    disc(716, 292, 92, (255, 216, 140), 0.55)
    disc(716, 292, 62, SUN_CORE)
    disc(716, 292, 46, (255, 248, 220))


def paint_clouds():
    # Three flat-bottomed dawn clouds, pale rose against the violet sky.
    for (cx, cy, rx, ry) in (
        (180, 210, 120, 26), (268, 228, 84, 20), (120, 232, 60, 16),
        (880, 150, 110, 22), (950, 168, 70, 16),
        (470, 120, 90, 18), (540, 134, 60, 13),
    ):
        ellipse(cx, cy, rx, ry, (255, 214, 196), 0.55)


def paint_birds():
    # Five distant birds: two short strokes meeting in a shallow V.
    for (bx, by, s) in ((300, 330, 9), (340, 306, 7), (392, 344, 8),
                        (600, 210, 8), (648, 236, 6), (520, 282, 7),
                        (560, 302, 6), (748, 178, 8), (796, 204, 6)):
        for k in range(s):
            span(by + k // 2, bx - s + k, bx - s + k, (52, 36, 66))
            span(by + k // 2, bx + k, bx + k, (52, 36, 66))


def paint_sea():
    for y in range(HORIZON, H):
        span(y, 0, W - 1, sea_at(y))
    # The sun's road: a widening column of gold shimmer below the sun.
    for y in range(HORIZON + 6, H - 8, 3):
        t = (y - HORIZON) / (H - HORIZON)
        half = int(34 + 150 * t)
        cx = 716
        # Broken dashes read as moving water better than a solid bar.
        for x in range(cx - half, cx + half, 26):
            dash = 14 + int(10 * (1.0 - t))
            blend_span(y, x, x + dash, (255, 200, 110), 0.55 * (1.0 - 0.7 * t))
            blend_span(y + 1, x + 4, x + dash + 2, (255, 214, 140), 0.35)


def paint_island(cx, top_y, rx, ry, tip_y, with_trees):
    """A floating island: grassy crown, rock body, tapering cliff."""
    # Cliff first so the crown overlaps its top edge cleanly.
    tapered_rock(cx, top_y + ry // 2, rx - 6, tip_y, ROCK, ROCK_DARK)
    # Rock body: an ellipse whose lower half the cliff continues.
    for dy in range(-ry, ry + 1):
        y = top_y + dy
        f = 1.0 - (dy / ry) ** 2
        if f < 0:
            continue
        dx = int(rx * (f ** 0.5))
        shade = mix(ROCK, ROCK_DARK, max(0.0, dy) / ry * 0.8)
        span(y, cx - dx, cx + dx, shade)
    # Grass crown: a shallow bright ellipse along the island's top.
    ellipse(cx, top_y - ry // 3, rx - 4, ry // 2, GRASS)
    ellipse(cx, top_y - ry // 3 - 4, rx - 26, ry // 3, (110, 176, 104))
    if with_trees:
        for (tx, ty, tr) in ((cx - rx // 2, top_y - 14, 12),
                             (cx - rx // 4, top_y - 20, 15),
                             (cx + rx // 3, top_y - 16, 11)):
            disc(tx, ty, tr, GRASS_DARK)
            disc(tx - 3, ty - 4, tr // 2, (72, 132, 80))


def paint_lighthouse(cx, base_y):
    """The poster's landmark: a white tower with red bands on the big island."""
    top_y = base_y - 168
    # Light beams sweep out before the tower is drawn over their roots.
    beam(cx, top_y + 14, cx - 330, top_y - 46, (255, 226, 150), 0.30)
    beam(cx, top_y + 14, cx + 330, top_y - 70, (255, 226, 150), 0.30)
    # Tower: a trapezoid, wider at the foot.
    for k in range(150):
        y = top_y + 18 + k
        t = k / 150
        half = int(13 + 15 * t)
        color = TOWER
        if 44 <= k < 66 or 104 <= k < 124:
            color = BAND
        span(y, cx - half, cx + half, color)
    # Gallery rail and lamp room.
    span(top_y + 16, cx - 20, cx + 20, (52, 40, 48))
    span(top_y + 17, cx - 20, cx + 20, (52, 40, 48))
    for k in range(16):
        y = top_y + k
        half = 12 - k // 4
        span(y, cx - half, cx + half, (52, 40, 48))
    disc(cx, top_y + 8, 9, LAMP)
    disc(cx, top_y + 8, 5, (255, 244, 200))
    # Roof cap.
    for k in range(7):
        span(top_y - 6 + k, cx - 9 + k, cx + 9 - k, BAND)
    # Door at the foot.
    for y in range(base_y - 26, base_y):
        span(y, cx - 6, cx + 6, (70, 52, 44))


def paint_reflections():
    # Dark, broken echoes of the islands on the water below the horizon.
    for (cx, rx, y0, length) in ((660, 210, HORIZON + 10, 90),
                                 (300, 140, HORIZON + 8, 64),
                                 (180, 70, HORIZON + 6, 40)):
        for k in range(length):
            y = y0 + k
            t = k / length
            half = int(rx * (1.0 - 0.6 * t))
            if k % 3 == 0:
                blend_span(y, cx - half, cx + half, (30, 52, 58), 0.45 * (1.0 - t))


def paint_frame():
    for t in range(4):
        span(18 + t, 18, W - 19, GOLD)
        span(H - 19 - t, 18, W - 19, GOLD)
        for y in range(18, H - 18):
            span(y, 18 + t, 18 + t, GOLD)
            span(y, W - 19 - t, W - 19 - t, GOLD)


def paint_poster():
    paint_sky()
    paint_sun()
    paint_clouds()
    paint_birds()
    paint_sea()
    paint_reflections()
    # Far, small island first; the big one with the lighthouse last.
    paint_island(178, 596, 74, 26, 668, False)
    paint_island(300, 566, 148, 40, 716, True)
    paint_island(660, 548, 228, 54, 768, True)
    paint_lighthouse(660, 548)
    # Title block: name first, then the line that says what the place is.
    draw_text_centered("VELMARA", 64, 13, CREAM, shadow=(30, 20, 60))
    draw_text_centered("THE ISLES THAT DRIFT", 168, 5, GOLD, shadow=(30, 20, 60))
    # A small gold rule with a diamond under the subtitle.
    span(206, 452, 560, GOLD)
    span(207, 452, 560, GOLD)
    for k in range(7):
        span(202 + k, 508 - k, 508 + k, GOLD)
    paint_frame()


# ---------------------------------------------------------------- PNG writer

def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    prev = bytearray(W * 3)
    for y in range(H):
        row = bytes(buf[y * W * 3:(y + 1) * W * 3])
        # Pick the cheapest of None / Sub / Up for this row.
        cands = []
        cands.append(b"\x00" + row)
        sub = bytearray(W * 3)
        for i in range(W * 3):
            left = row[i - 3] if i >= 3 else 0
            sub[i] = (row[i] - left) & 0xFF
        cands.append(b"\x01" + bytes(sub))
        up = bytes((row[i] - prev[i]) & 0xFF for i in range(W * 3))
        cands.append(b"\x02" + up)
        best = min(cands, key=lambda c: sum(b if b < 128 else 256 - b for b in c[1:]))
        raw += best
        prev = bytearray(row)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    paint_poster()
    out_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print(f"wrote {path} ({size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
