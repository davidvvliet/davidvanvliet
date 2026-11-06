"""Draws marking-mask.png: the MPU-6050's laser marking as even, round-ended strokes.

Every character's box (left, right, top, bottom) and each row's stroke width were measured
on the spekking_nexus7 photo, rectified by the package's four corners to 800 x 800 px
(200 px/mm; see specs/mpu6050.json, marking). Each glyph is that character's centre line as
seen in the photo, drawn inside its box. A plain threshold of the photo came out ragged:
the strokes are only ~13 px wide there, on speckled mould compound.

    python3 refs/mpu6050/marking-draw.py   (from scripts/blender; writes the mask beside it)
"""
import math
import os

from PIL import Image, ImageDraw

OUT = 1600          # mask size, px (the photo measurements are in 800 px space)
SS = 4              # supersampling for smooth edges
K = OUT * SS / 800  # 800 px space -> drawing space


def arc(cx, cy, rx, ry, a0, a1, n=24):
    """Points on an ellipse in the glyph's unit box (v down), angles in degrees (90 = down)."""
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def flip(strokes):
    return [[(1 - u, 1 - v) for u, v in s] for s in strokes]


# Centre lines in a unit box: u right, v down, 0..1 between the stroke centres.
G = {
    "I": [[(0.5, 0), (0.5, 1)]],
    "N": [[(0, 1), (0, 0), (1, 1), (1, 0)]],
    "V": [[(0, 0), (0.5, 1), (1, 0)]],
    "E": [[(1, 0), (0, 0), (0, 1), (1, 1)], [(0, 0.5), (0.86, 0.5)]],
    "L": [[(0, 0), (0, 1), (1, 1)]],
    "M": [[(0, 1), (0, 0), (0.5, 0.62), (1, 0), (1, 1)]],
    "P": [[(0, 1), (0, 0), (0.62, 0)] + arc(0.62, 0.27, 0.38, 0.27, -90, 90) + [(0, 0.54)]],
    "U": [[(0, 0), (0, 0.66)] + arc(0.5, 0.66, 0.5, 0.34, 180, 0) + [(1, 0)]],
    "D": [[(0, 0), (0.42, 0)] + arc(0.42, 0.38, 0.58, 0.38, -90, 0)
          + arc(0.42, 0.62, 0.58, 0.38, 0, 90) + [(0, 1), (0, 0)]],
    "S": [arc(0.5, 0.26, 0.48, 0.26, 335, 125) + arc(0.5, 0.74, 0.5, 0.26, -55, 155)],
    "G": [arc(0.5, 0.3, 0.5, 0.3, 330, 180) + arc(0.5, 0.7, 0.5, 0.3, 180, 0)
          + [(1, 0.53), (0.56, 0.53)]],
    "0": [arc(0.5, 0.3, 0.5, 0.3, 180, 360) + arc(0.5, 0.7, 0.5, 0.3, 0, 180) + [(0, 0.3)]],
    "6": [arc(0.5, 0.3, 0.5, 0.3, 325, 180) + [(0, 0.69)], arc(0.5, 0.69, 0.5, 0.31, 0, 360, 48)],
    "5": [[(0.95, 0), (0.06, 0), (0.03, 0.47)] + arc(0.47, 0.68, 0.53, 0.32, -150, 150)],
    "2": [arc(0.5, 0.27, 0.5, 0.27, 195, 380) + [(0, 1), (1, 1)]],
    "8": [arc(0.5, 0.24, 0.44, 0.24, 0, 360, 48), arc(0.5, 0.72, 0.5, 0.28, 0, 360, 48)],
    "4": [[(0.72, 1), (0.72, 0), (0, 0.68), (1, 0.68)]],
    "1": [[(0, 0.22), (0.75, 0), (0.75, 1)]],
    "-": [[(0, 0.5), (1, 0.5)]],
}
G["9"] = flip(G["6"])

# Rows: (top, bottom, stroke width), then (character, left, right) in 800 px space.
ROWS = [
    ((220, 303, 13), [("I", 50, 63), ("N", 67, 135), ("V", 142, 213), ("E", 216, 283),
                      ("N", 294, 362), ("S", 371, 436), ("E", 441, 508), ("N", 518, 586),
                      ("S", 595, 660), ("E", 666, 733)]),
    ((340, 428, 13), [("M", 98, 165), ("P", 177, 234), ("U", 245, 314), ("-", 324, 380),
                      ("6", 402, 454), ("0", 471, 536), ("5", 552, 608), ("0", 618, 688)]),
    ((490, 592, 17), [("D", 79, 138), ("2", 151, 200), ("G", 216, 269), ("5", 283, 337),
                      ("9", 351, 405), ("4", 420, 469), ("L", 548, 604), ("1", 625, 658)]),
    ((612, 716, 17), [("E", 80, 137), ("I", 165, 190), ("1", 288, 324), ("2", 350, 403),
                      ("2", 420, 469), ("8", 485, 540), ("D", 616, 674)]),
]
DOT = (80, 103, 39)  # pin 1 dot: centre and radius, 800 px space

img = Image.new("L", (OUT * SS,) * 2, 0)
d = ImageDraw.Draw(img)
cx, cy, r = (v * K for v in DOT)
d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
for (top, bottom, w), chars in ROWS:
    h = w / 2
    for ch, x0, x1 in chars:
        y0, y1 = top, bottom
        if ch == "-":  # the dash's own height, centred on y 377
            y0 = y1 = 377
        bx0, bx1, by0, by1 = x0 + h, x1 - h, y0 + h, y1 - h
        for s in G[ch]:
            pts = [((bx0 + u * (bx1 - bx0)) * K, (by0 + v * (by1 - by0)) * K) for u, v in s]
            d.line(pts, fill=255, width=round(w * K), joint="curve")
            for x, y in (pts[0], pts[-1]):  # round ends
                d.ellipse((x - h * K, y - h * K, x + h * K, y + h * K), fill=255)
img.resize((OUT, OUT), Image.LANCZOS).save(os.path.join(os.path.dirname(__file__), "marking-mask.png"))
