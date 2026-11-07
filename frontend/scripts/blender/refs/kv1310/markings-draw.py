"""Draws the KV-1310's front labels as masks (white = print), one PNG per label, each covering
its plate exactly. Every label's box, letter height and spacing were measured on the front of
kahaku_00063, rectified to 2 px/mm (specs/kv1310.json, from_photos.layout); the letters are
even strokes along each character's centre line as seen there (a wide sans for the small
labels, a serif for SONY). The photo itself can't be reproduced, so nothing is copied from it.

    python3 refs/kv1310/markings-draw.py   (from scripts/blender; writes refs/kv1310/labels/)
"""
import math
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels")
PX = 24   # px per mm in the masks
SS = 3    # supersampling


def arc(cx, cy, rx, ry, a0, a1, n=20):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


# Wide sans, centre lines in a unit box (u right, v down). Rounded letters are stadium-like,
# as the extended face on the set.
r = 0.32
SANS = {
    "S": [arc(0.5, 0.26, 0.49, 0.26, 335, 125) + arc(0.5, 0.74, 0.5, 0.26, -55, 155)],
    "O": [arc(r, r, r, r, 180, 270) + arc(1 - r, r, r, r, 270, 360) + arc(1 - r, 1 - r, r, r, 0, 90)
          + arc(r, 1 - r, r, r, 90, 180) + [(0, r)]],
    "C": [arc(1 - r, r, r, r, -20, -90)[0:] + arc(r, r, r, r, 270, 180)[1:] + [(0, 1 - r)]
          + arc(r, 1 - r, r, r, 180, 90)[1:] + arc(1 - r, 1 - r, r, r, 90, 20)[1:]],
    "D": [[(0, 0), (1 - r, 0)] + arc(1 - r, r, r, r, 270, 360)[1:] + [(1, 1 - r)] + arc(1 - r, 1 - r, r, r, 0, 90)[1:]
          + [(0, 1), (0, 0)]],
    "L": [[(0, 0), (0, 1), (1, 1)]],
    "I": [[(0.5, 0), (0.5, 1)]],
    "T": [[(0, 0), (1, 0)], [(0.5, 0), (0.5, 1)]],
    "A": [[(0, 1), (0.5, 0), (1, 1)], [(0.22, 0.62), (0.78, 0.62)]],
    "E": [[(1, 0), (0, 0), (0, 1), (1, 1)], [(0, 0.5), (0.85, 0.5)]],
    "N": [[(0, 1), (0, 0), (1, 1), (1, 0)]],
    "R": [[(0, 1), (0, 0), (1 - r, 0)] + arc(1 - r, 0.25, r, 0.25, 270, 450)[1:] + [(0, 0.5)], [(0.55, 0.5), (1, 1)]],
    "|": [[(0.5, -0.15), (0.5, 1.15)]],
    " ": [],
}
SANS_W = {"I": 0.0, "|": 0.0, " ": 0.9, "T": 1.0, "A": 1.15}

# Digits for the channel ring (narrower, plain).
DIG = {
    "0": [arc(0.5, 0.5, 0.5, 0.5, 0, 360, 32)],
    "1": [[(0.2, 0.2), (0.6, 0), (0.6, 1)]],
    "2": [arc(0.5, 0.28, 0.5, 0.28, 190, 380) + [(0, 1), (1, 1)]],
    "3": [arc(0.5, 0.26, 0.48, 0.26, 200, 450) + arc(0.5, 0.74, 0.5, 0.26, -90, 160)],
    "4": [[(0.72, 1), (0.72, 0), (0, 0.68), (1, 0.68)]],
    "5": [[(0.95, 0), (0.06, 0), (0.03, 0.47)] + arc(0.47, 0.68, 0.53, 0.32, -150, 150)],
    "6": [arc(0.5, 0.3, 0.5, 0.3, 325, 180) + [(0, 0.69)], arc(0.5, 0.69, 0.5, 0.31, 0, 360, 32)],
    "7": [[(0, 0), (1, 0), (0.35, 1)]],
    "8": [arc(0.5, 0.24, 0.44, 0.24, 0, 360, 32), arc(0.5, 0.72, 0.5, 0.28, 0, 360, 32)],
    "9": None,
}
DIG["9"] = [[(1 - u, 1 - v) for u, v in s] for s in DIG["6"]]


class Canvas:
    def __init__(self, w_mm, h_mm):
        self.w, self.h = w_mm, h_mm
        self.k = PX * SS
        self.im = Image.new("L", (round(w_mm * self.k), round(h_mm * self.k)), 0)
        self.d = ImageDraw.Draw(self.im)

    def strokes(self, strokes, x0, y0, w, h, sw, rot=None):
        """Draw unit-box strokes into the box (x0, y0, w, h) mm, stroke width sw mm; `rot`:
        (cx, cy, deg) turns the result about a point (mm)."""
        k, hw = self.k, sw / 2
        for s in strokes:
            pts = []
            for u, v in s:
                x, y = x0 + hw + u * (w - sw), y0 + hw + v * (h - sw)
                if rot:
                    cx, cy, a = rot
                    c, si = math.cos(math.radians(a)), math.sin(math.radians(a))
                    x, y = cx + (x - cx) * c - (y - cy) * si, cy + (x - cx) * si + (y - cy) * c
                pts.append((x * k, y * k))
            if len(pts) > 1:
                self.d.line(pts, fill=255, width=max(1, round(sw * k)), joint="curve")
            for x, y in (pts[0], pts[-1]):
                self.d.ellipse((x - hw * k, y - hw * k, x + hw * k, y + hw * k), fill=255)

    def rect(self, x0, y0, x1, y1):
        k = self.k
        self.d.rectangle((x0 * k, y0 * k, x1 * k, y1 * k), fill=255)

    def text(self, s, x0, y0, cap, sw, adv=1.25, gap=0.45):
        """Wide sans text from x0 (mm), cap height `cap`, letters `adv` caps wide."""
        x = x0
        for ch in s:
            w = cap * SANS_W.get(ch, adv) if ch not in ("I", "|") else sw
            if ch in ("I", "|"):
                self.strokes(SANS[ch], x - (cap * 0.5 - sw) / 2 * 0, y0, sw, cap, sw)
                x += sw + gap * cap
                continue
            self.strokes(SANS[ch], x, y0, w, cap, sw)
            x += w + gap * cap
        return x

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        self.im.resize((round(self.w * PX), round(self.h * PX)), Image.LANCZOS).save(os.path.join(OUT, name))


def text_width(s, cap, sw, adv=1.25, gap=0.45):
    w = 0
    for ch in s:
        w += (sw if ch in ("I", "|") else cap * SANS_W.get(ch, adv)) + gap * cap
    return w - gap * cap


# 1. SONY plate [136, 286, 201, 297]: bars at u 138.8 and 200 (just inside the plate's ends),
#    letters u 147.5-192, caps 6.5 mm from v 288.
c = Canvas(65, 11)
c.rect(2.3, 1.5, 3.0, 9.5)
c.rect(62.3, 1.5, 63.0, 9.5)
# serif SONY: four letters over 44.5 mm, 6.5 mm caps, heavy strokes with slab serifs
x0, cap, sw = 11.5, 6.5, 1.15
cell = 44.5 / 4
y0 = 2.0
ser = [[(-0.12, 0), (0.12, 0)], [(-0.12, 1), (0.12, 1)]]
S_ser = SANS["S"]
c.strokes(S_ser, x0 + 0.6, y0, cell - 1.8, cap, sw)
c.strokes(SANS["O"], x0 + cell + 0.3, y0, cell - 1.2, cap, sw)
c.strokes([[(0, 1), (0, 0), (1, 1), (1, 0)]], x0 + 2 * cell + 0.6, y0, cell - 1.8, cap, sw * 0.8)
for u in (0, 1):
    c.strokes([[(u - 0.15, 0), (u + 0.15, 0)]], x0 + 2 * cell + 0.6, y0, cell - 1.8, cap, sw * 0.6)
c.strokes([[(0.15, 1), (-0.1, 1)]], x0 + 2 * cell + 0.6, y0, cell - 1.8, cap, sw * 0.6)
c.strokes([[(0, 0), (0.5, 0.55), (1, 0)], [(0.5, 0.55), (0.5, 1)], [(-0.1, 0), (0.18, 0)],
           [(0.82, 0), (1.1, 0)], [(0.3, 1), (0.7, 1)]], x0 + 3 * cell + 0.3, y0, cell - 1.2, cap, sw * 0.85)
c.save("sony_plate.png")

# 2. Front text [205, 311, 345, 320]: "SOLID STATE" u 208-259, divider u 265,
#    "TRINITRON COLOR" u 271-340; caps 2.8 mm from v 314.
c = Canvas(140, 9)
cap, sw = 2.8, 0.45
for s, u0, u1 in (("SOLID STATE", 208, 259), ("TRINITRON COLOR", 271, 340)):
    w0 = text_width(s, cap, sw)
    adv = 1.25 * (u1 - u0) / w0
    c.text(s, u0 - 205, 3.0, cap, sw, adv=adv, gap=0.45 * (u1 - u0) / w0)
c.rect(265 - 205 - 0.25, 2.2, 265 - 205 + 0.25, 7.0)
c.save("front_text.png")

# 3. Badge [344, 167.5, 412.5, 180]: "TRINITRON" u 347.5-409, caps 3.5 mm from v 169.5;
#    three bars below it, v 175-178.5, each a third of the badge with 1 mm gaps.
cap, sw = 3.5, 0.55
w0 = text_width("TRINITRON", cap, sw)
layers = {}
c = Canvas(68.5, 12.5)
c.text("TRINITRON", 3.5, 1.8, cap, sw, adv=1.25 * 61.5 / w0, gap=0.45 * 61.5 / w0)
c.save("badge_text.png")
for i, nm in enumerate(("blue", "red", "green")):
    c = Canvas(68.5, 12.5)
    w = (68.5 - 4) / 3
    c.rect(1 + i * (w + 1), 7.5, 1 + i * (w + 1) + w, 11.0)
    c.save(f"badge_{nm}.png")

# 4. COLOR plate [373.5, 192.5, 383.5, 207.5]: a thin frame line and "COLOR" across it,
#    condensed, caps 4 mm.
c = Canvas(10, 15)
c.rect(0.6, 0.6, 9.4, 1.0)
c.rect(9.0, 0.6, 9.4, 14.4)
cap, sw = 4.0, 0.55
x = 0.9
for ch in "COLOR":
    w = 1.4 if ch != "L" else 1.15
    c.strokes(SANS[ch], x, 5.5, w, cap, sw)
    x += w + 0.22
c.save("color_plate.png")

# 5. Channel ring: numbers 1-12 round the dial face (radius 18.9 mm, the dial_face), 6 at the
#    top, rising counter-clockwise from 1 near four o'clock, 22 degrees apart (photo).
R = 18.9
c = Canvas(2 * R, 2 * R)
cap, sw = 3.2, 0.5
for n in range(1, 13):
    a = (n - 6) * 22.0                        # degrees counter-clockwise from the top
    rr = R - 3.0
    cx = R - rr * math.sin(math.radians(a))
    cy = R - rr * math.cos(math.radians(a))
    digits = str(n)
    dw = 1.9
    tot = len(digits) * dw + (len(digits) - 1) * 0.35
    for i, ch in enumerate(digits):
        x = cx - tot / 2 + i * (dw + 0.35)
        c.strokes(DIG[ch], x, cy - cap / 2, dw, cap, sw, rot=(cx, cy, -a))
c.save("dial_numbers.png")
print("written", sorted(os.listdir(OUT)))
