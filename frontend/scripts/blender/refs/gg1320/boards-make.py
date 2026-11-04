"""Board textures and outlines for gg1320, from Samuel M. Goldwasser's GG1320AN photos.

Usage: python3 -I boards-make.py <photo folder> <out folder>

Each board side's photo is resampled into the model's frame, seen from above (+x right, +y
up), over a square 2 * HALF wide centred on the case axis. A photo taken of a downward side
is mirrored left to right on the way. Pixels off the board (cloth, the aluminium can, the
flex) are filled with the board's green. Each board's outline is read from its first photo:
for every angle, walking in from the housing's wall, the first point where the board's green or
gold edge starts.
"""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw

HALF = 0.042  # m, half the texture's width (the housing's outer radius)
N = 1024

# centre_px: the case axis in the photo; px_per_mm: the board's scale; below: the photo looks
# at a side that faces down in the gyro.
BOARDS = {
    "pcb1": [  # the hexagonal board, lower; its chip side faces up
        {"photo": "gg1320anpcb1_bottom_closeup1.jpg", "side": "top", "centre_px": [512, 490], "px_per_mm": 11.33,
         "below": False},
        {"photo": "gg1320anpcb1_top_closeup1.jpg", "side": "bottom", "centre_px": [512, 505], "px_per_mm": 11.46,
         "below": True},
    ],
    "pcb2": [  # the D-shaped board, upper; its hybrid side faces down
        {"photo": "gg1320anpcb2_top_closeup1.jpg", "side": "bottom", "centre_px": [512, 492], "px_per_mm": 13.1,
         "below": True},
        {"photo": "gg1320anpcb2_bottom_closeup1.jpg", "side": "top", "centre_px": [505, 463], "px_per_mm": 12.8,
         "below": False},
    ],
}


def board_mask(rgb):
    """The board's own colours: its green and the gold edge plating."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    green = (g > r + 15) & (g > b)
    gold = (r > 140) & (g > 110) & (b < 110) & (r - b > 60)
    return green | gold


def sampler(view):
    cx, cy = view["centre_px"]
    k = view["px_per_mm"] * 1000.0
    s = -1.0 if view["below"] else 1.0
    return lambda x, y: (cx + s * x * k, cy - y * k)


def outline(img, mask, view, n=120):
    to_px = sampler(view)
    h, w = mask.shape
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 0.040
        found = None
        run = 0
        while r > 0.015:  # from the housing's inside wall inwards
            px, py = to_px(r * math.cos(a), r * math.sin(a))
            ix, iy = int(round(px)), int(round(py))
            on = 0 <= ix < w and 0 <= iy < h and mask[iy, ix]
            run = run + 1 if on else 0
            if run >= 6:  # 0.6 mm of board in a row
                found = r + 0.0005
                break
            r -= 0.0001
        pts.append(found)
    # A running median over 5 angles takes out single-ray misses (a part near the edge).
    rs = [sorted(pts[(i + j) % n] for j in range(-2, 3))[2] for i in range(n)]
    return [[round(r * math.cos(2 * math.pi * i / n), 5), round(r * math.sin(2 * math.pi * i / n), 5)]
            for i, r in enumerate(rs)]


def texture(img, inside, view, green):
    """`inside`: the outline as photo pixels; everything outside it is filled with green."""
    to_px = sampler(view)
    cx, cy = to_px(-HALF, HALF)  # the texture's top-left corner
    step = 2 * HALF / N
    k = view["px_per_mm"] * 1000.0
    s = -1.0 if view["below"] else 1.0
    poly = Image.new("L", (img.shape[1], img.shape[0]), 0)
    ImageDraw.Draw(poly).polygon([to_px(x, y) for x, y in inside], fill=255)
    filled = img.copy()
    filled[np.asarray(poly) == 0] = green
    pil = Image.fromarray(filled)
    return pil.transform((N, N), Image.AFFINE, (s * step * k, 0, cx, 0, step * k, cy), resample=Image.BICUBIC,
                         fillcolor=tuple(int(c) for c in green))


def main(src, out):
    outlines = {}
    for board, views in BOARDS.items():
        for j, view in enumerate(views):
            img = np.asarray(Image.open(f"{src}/{view['photo']}").convert("RGB"))
            mask = board_mask(img)
            green = np.median(img[mask & (img[..., 1] > img[..., 0] + 30) & (img[..., 1] > img[..., 2] + 10)], axis=0)
            if j == 0:
                outlines[board] = outline(img, mask, view)
            texture(img, outlines[board], view, green).save(f"{out}/{board}-{view['side']}.jpg", quality=86)
    json.dump({"half": HALF, "boards": BOARDS, "outlines": outlines}, open(f"{out}/boards.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
