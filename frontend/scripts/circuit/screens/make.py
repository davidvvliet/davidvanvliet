# Draws the pictures the boards' screens show in their web models (python3 screens/make.py):
#   boards/muse-voice/screen.png   Vega, David's Muse avatar, as pixel art (the Muse SDK draws avatars at 64x64,
#                                  avatar/muse_pixel.c), at the round panel's 240x240
#   boards/air-quality/screen.png  the e-paper's 200x200 black and white, with sample readings (not measured)
# Text in Pillow's built-in font (Aileron, SIL Open Font Licence).
import math, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BOARDS = os.path.join(HERE, "..", "boards")

def star(cx, cy, r_out, r_in, rot=-math.pi / 2):
    return [(cx + (r_out if i % 2 == 0 else r_in) * math.cos(rot + i * math.pi / 5),
             cy + (r_out if i % 2 == 0 else r_in) * math.sin(rot + i * math.pi / 5)) for i in range(10)]

def vega(size=240, grid=64):
    """A plump pale-blue star with five equal rounded points and two dot eyes, lit from above, on black: drawn
    at 64x64 like the SDK's avatars, its left half mirrored so both sides match, then scaled up."""
    s = 16
    big = grid * s
    pts = star(0, 0, 1, 0.58)
    top, bot = -1, max(y for _, y in pts)            # centred on its own height, not its centre
    r = big * 0.46
    cy = big / 2 - (top + bot) / 2 * r
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).polygon([(big / 2 + x * r, cy + y * r) for x, y in pts], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(big * 0.035)).point(lambda v: 255 if v > 150 else 0)  # equal round tips
    mask = mask.resize((grid, grid), Image.BOX)
    shades = [(232, 240, 252), (214, 226, 248), (196, 212, 242), (178, 196, 234), (158, 178, 222), (136, 156, 204)]
    px = Image.new("RGB", (grid, grid), (0, 0, 0))
    half = grid // 2
    for y in range(grid):
        for x in range(half):
            a = mask.getpixel((x, y))
            if a < 128: continue
            d = math.hypot(x + 0.5 - half, y - grid * 0.22) / (grid * 0.6)   # light above the middle
            k = min(len(shades) - 1, int(d * len(shades) + ((x + y) % 2) * 0.5))
            c = shades[k]
            px.putpixel((x, y), c); px.putpixel((grid - 1 - x, y), c)
    ey = round(cy / s + 0.06 * grid)
    for ex in (half - 4, half + 2):  # the eyes, equally either side of the middle
        for dx in (0, 1):
            for dy in (0, 1):
                px.putpixel((ex + dx, ey + dy), (20, 24, 36))
    up = px.resize((grid * 4, grid * 4), Image.NEAREST)  # 256: the middle 240 (the edges are black)
    o = (grid * 4 - size) // 2
    return up.crop((o, o, o + size, o + size))

def epaper(size=200):
    img = Image.new("L", (size, size), 255)
    d = ImageDraw.Draw(img)
    big, mid, small = (ImageFont.load_default(size=s) for s in (44, 22, 14))
    d.text((10, 8), "AIR QUALITY", font=small, fill=0)
    d.line((10, 28, 190, 28), fill=0, width=2)
    d.text((10, 36), "CO2", font=small, fill=0)
    d.text((10, 50), "612", font=big, fill=0)
    d.text((100, 72), "ppm", font=mid, fill=0)
    d.line((10, 104, 190, 104), fill=0, width=1)
    d.text((10, 112), "VOC", font=small, fill=0); d.text((10, 128), "102", font=mid, fill=0)
    d.text((105, 112), "PM2.5", font=small, fill=0); d.text((105, 128), "4", font=mid, fill=0)
    d.text((128, 135), "ug/m3", font=small, fill=0)
    d.line((10, 160, 190, 160), fill=0, width=1)
    d.text((10, 168), "sample readings", font=small, fill=0)
    return img.point(lambda v: 0 if v < 128 else 255).convert("1")

if __name__ == "__main__":
    vega().save(os.path.join(BOARDS, "muse-voice", "screen.png"))
    epaper().save(os.path.join(BOARDS, "air-quality", "screen.png"))
