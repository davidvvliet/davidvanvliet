# Draws refs/aether/sled-lettering-mask.png: the lettering on the back of Aether's sled, in Geist.
# "Altair" on top, "LAUNCH" right below it at half the size (as "ULTRALIGHT" is to "Altair" on the
# finrocket: 114 px to 1.2 x 190 px), both centred; a gap, then the motto in capitals.
#   python3 scripts/blender/tools/sled_lettering.py [Geist-Regular.ttf]     (from frontend/)
import os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "refs", "aether", "sled-lettering-mask.png")
FONT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "..", "..", "..", "node_modules", "next", "dist", "compiled", "@vercel", "og", "Geist-Regular.ttf")

BIG = 228                 # "Altair"
SMALL = BIG // 2          # "LAUNCH", as "ULTRALIGHT" on the rocket
MOTTO = 66
LINES = ["WE GO TO SPACE", "TO IMPROVE LIFE ON EARTH"]
W, PAD = 1400, 30

big, small, motto = (ImageFont.truetype(FONT, s) for s in (BIG, SMALL, MOTTO))
img = Image.new("L", (W, 1000), 0)
g = ImageDraw.Draw(img)

# "Altair" centred on top, "LAUNCH" centred right below it ("ms" anchor: middle, baseline).
base = PAD + big.getmetrics()[0]
g.text((W / 2, base), "Altair", font=big, fill=255, anchor="ms")
base += 0.12 * BIG + small.getmetrics()[0]
g.text((W / 2, base), "LAUNCH", font=small, fill=255, anchor="ms")

# A gap, then the motto, centred, two lines.
y = base + 0.9 * SMALL
for line in LINES:
    y += motto.getmetrics()[0]
    g.text((W / 2, y), line, font=motto, fill=255, anchor="ms")
    y += 0.35 * MOTTO

l, t, r, b = img.getbbox()
img = img.crop((max(0, l - PAD), max(0, t - PAD), r + PAD, b + PAD))   # the text fills the sheet
os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT)
print(OUT, img.size)
