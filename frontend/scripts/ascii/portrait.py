"""Portrait photo -> plain ASCII text for a dark page (bright = dense glyph).

usage: python3 -I portrait.py IMAGE FONT.ttf OUT.txt COLS CROP [MIX] [GAMMA] [LEVELS] [BLACK] [FLOOD]
  CROP  = x0,y0,x1,y1 as fractions of the image
  MIX   = local-contrast strength (0xSero/ascii-art's photo_dots.py idea), default 0.6
  GAMMA = <1 lifts darks, >1 deepens them, default 1.0
  LEVELS= how many characters in the ramp, default 14
  BLACK = percentile of the photo that becomes blank (the background), default 2
  FLOOD = faint cells joined to the edge below this level are cleared as background, default 0 (off)

The thinkers page (app/thinkers) was made with Roboto Mono (google/fonts, ofl/robotomono) and:
  portrait.py newton.jpeg RobotoMono.ttf newton.txt 80 0.26,0.08,0.74,0.45 0.4 1.1 14 25 0.17
  portrait.py darwin.jpeg RobotoMono.ttf darwin.txt 60 0.25,0.08,0.85,0.7 0.3 1.3 14 30 0.17
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

img, font_path, out, cols, crop = sys.argv[1:6]
cols = int(cols)
mix = float(sys.argv[6]) if len(sys.argv) > 6 else 0.6
gamma = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
levels = int(sys.argv[8]) if len(sys.argv) > 8 else 14
LINE = 1.2  # line-height the page will use

# --- ink each printable ASCII glyph covers in the page's font (ascii-magic-art's idea)
font = ImageFont.truetype(font_path, 100)
cw = font.getlength("M")
ch = 100 * LINE
ink = {}
for c in map(chr, range(32, 127)):
    cell = Image.new("L", (int(cw), int(ch)), 0)
    ImageDraw.Draw(cell).text((0, (ch - 100) / 2), c, font=font, fill=255)
    ink[c] = np.asarray(cell).mean() / 255
top = max(ink.values())
glyphs = sorted(ink, key=ink.get)
# pick LEVELS glyphs whose ink is evenly spaced from blank to the densest
ramp = []
for t in np.linspace(0, top, levels):
    best = min(glyphs, key=lambda c: abs(ink[c] - t))
    if best not in ramp:
        ramp.append(best)
vals = np.array([ink[c] for c in ramp]) / top

# --- the photo: crop, grey, local contrast, levels from the subject's own tones (0xSero's idea)
im = Image.open(img).convert("L")
W, H = im.size
x0, y0, x1, y1 = (float(v) for v in crop.split(","))
im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
a = np.asarray(im).astype(float) / 255
big = np.asarray(im.filter(ImageFilter.GaussianBlur(im.width / 12))).astype(float) / 255
a = a - mix * big + mix * big.mean()
lo, hi = np.percentile(a, [float(sys.argv[9]) if len(sys.argv) > 9 else 2, 99.5])
a = np.clip((a - lo) / (hi - lo), 0, 1) ** gamma

# --- one value per character cell (area average), cell aspect from the font
rows = round(cols * (im.height / im.width) * (cw / ch))
small = Image.fromarray((a * 255).astype(np.uint8)).resize((cols, rows), Image.BOX)
v = np.asarray(small).astype(float) / 255
v[v < 0.07] = 0  # faint specks in the background read as noise

# FLOOD: blank every faint cell (below FLOOD) joined to the picture's edge through faint cells:
# that is the background. Faint shading inside the figure is enclosed by it and stays.
flood = float(sys.argv[10]) if len(sys.argv) > 10 else 0
if flood:
    faint = v < flood
    seen = np.zeros_like(faint)
    stack = [(r, c) for r in range(v.shape[0]) for c in (0, v.shape[1] - 1)] + \
            [(r, c) for c in range(v.shape[1]) for r in (0, v.shape[0] - 1)]
    while stack:
        r, c = stack.pop()
        if not (0 <= r < v.shape[0] and 0 <= c < v.shape[1]) or seen[r, c] or not faint[r, c]:
            continue
        seen[r, c] = True
        stack += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
    v[seen] = 0

# Specks: drop little islands of ink (under 6 cells) that touch nothing else.
seen = np.zeros(v.shape, bool)
for r0 in range(v.shape[0]):
    for c0 in range(v.shape[1]):
        if v[r0, c0] == 0 or seen[r0, c0]:
            continue
        group, stack = [], [(r0, c0)]
        while stack:
            r, c = stack.pop()
            if not (0 <= r < v.shape[0] and 0 <= c < v.shape[1]) or seen[r, c] or v[r, c] == 0:
                continue
            seen[r, c] = True
            group.append((r, c))
            stack += [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
        if len(group) < 6:
            for r, c in group:
                v[r, c] = 0

lines = []
for r in v:
    lines.append("".join(ramp[int(np.abs(vals - x).argmin())] for x in r).rstrip())
open(out, "w").write("\n".join(lines) + "\n")
print(f"{cols}x{rows} ramp={''.join(ramp)!r}", file=sys.stderr)
