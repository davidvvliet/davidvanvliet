# Draws Aether's lettering masks in the finrocket's style: Geist Regular with a 4 px outline at 114 px
# (refs/finrocket/lettering-mask.png matches that within 2 %: its "ULTRALIGHT" is Geist at 114 px with a
# 4 px stroke; its "Altair" the same at 190 px, scaled up 20 %). Other sizes keep the outline in proportion.
# refs/aether/sled-lettering-mask.png, the back of the sled's pusher:
# "Altair" on top, "LAUNCH" right below it at half its size, both centred; a gap, then the motto in capitals.
# refs/aether/craft-lettering-mask.png, the craft's sides: "Altair AETHER" as the finrocket's
# "Altair ULTRALIGHT", the second word half the size, on one baseline.
#   python3 scripts/blender/tools/sled_lettering.py [Geist-Regular.ttf]     (from frontend/)
import os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "refs", "aether")
FONT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "..", "..", "..", "node_modules", "next", "dist", "compiled", "@vercel", "og", "Geist-Regular.ttf")

ALTAIR, SCALE = 190, 1.2  # "Altair" drawn at 190 px, then scaled up 20 % (228 px), as on the rocket
SMALL = 114               # "LAUNCH", "AETHER": as "ULTRALIGHT"
MOTTO = 66
LINES = ["WE GO TO SPACE", "TO IMPROVE LIFE ON EARTH"]
STROKE = 4 / 114          # the outline, as a share of the font size
PAD = 30


def word(text, size, scale=1.0):
    """One word as a mask: drawn with the outline, cropped, scaled; and its baseline from the top."""
    f = ImageFont.truetype(FONT, size)
    s = round(STROKE * size)
    asc, desc = f.getmetrics()
    img = Image.new("L", (int(f.getlength(text)) + 4 * s + 20, asc + desc + 4 * s + 20), 0)
    ImageDraw.Draw(img).text((2 * s + 10, 2 * s + 10 + asc), text, font=f, fill=255, anchor="ls",
                             stroke_width=s, stroke_fill=255)
    l, t, r, b = img.getbbox()
    img, base = img.crop((l, t, r, b)), 2 * s + 10 + asc - t
    if scale != 1.0:
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        base = base * scale
    return img, base


def save(img, name):
    l, t, r, b = img.getbbox()
    img = img.crop((max(0, l - PAD), max(0, t - PAD), r + PAD, b + PAD))   # the text fills the sheet
    os.makedirs(REFS, exist_ok=True)
    out = os.path.join(REFS, name)
    img.save(out)
    print(out, img.size)


altair, a_base = word("Altair", ALTAIR, SCALE)

# The sled: "Altair" centred on top, "LAUNCH" centred right below it, a gap, then the motto, centred.
W = 1600
img = Image.new("L", (W, 1200), 0)
y = PAD
img.paste(altair, ((W - altair.width) // 2, y)); y += altair.height + round(0.12 * ALTAIR * SCALE)
launch, _ = word("LAUNCH", SMALL)
img.paste(launch, ((W - launch.width) // 2, y)); y += launch.height + round(0.9 * SMALL)
for line in LINES:
    m, _ = word(line, MOTTO)
    img.paste(m, ((W - m.width) // 2, y)); y += m.height + round(0.45 * MOTTO)
save(img, "sled-lettering-mask.png")

# The craft: "Altair AETHER" on one baseline, a space of the small size between the words.
aether, e_base = word("AETHER", SMALL)
gap = round(ImageFont.truetype(FONT, SMALL).getlength(" ")) + round(STROKE * SMALL) * 2
img = Image.new("L", (altair.width + gap + aether.width + 2 * PAD, altair.height + 2 * PAD), 0)
img.paste(altair, (PAD, PAD))
img.paste(aether, (PAD + altair.width + gap, PAD + round(a_base - e_base)))
save(img, "craft-lettering-mask.png")
