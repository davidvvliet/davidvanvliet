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

def vega(size=240, grid=60):
    """A plump pale-blue star with rounded points and two dot eyes, lit from the top left, on black."""
    s = 8
    mask = Image.new("L", (grid * s, grid * s), 0)
    ImageDraw.Draw(mask).polygon(star(grid * s / 2, grid * s * 0.54, grid * s * 0.44, grid * s * 0.29), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(grid * s * 0.045)).point(lambda v: 255 if v > 140 else 0)  # rounded points
    mask = mask.resize((grid, grid), Image.LANCZOS)
    shades = [(232, 240, 252), (214, 226, 248), (196, 212, 242), (178, 196, 234), (158, 178, 222), (136, 156, 204)]
    lx, ly = grid * 0.38, grid * 0.30  # the light
    px = Image.new("RGB", (grid, grid), (0, 0, 0))
    for y in range(grid):
        for x in range(grid):
            a = mask.getpixel((x, y))
            if a < 110: continue
            d = math.hypot(x - lx, y - ly) / (grid * 0.55)
            k = min(len(shades) - 1, int(d * len(shades) + ((x + y) % 2) * 0.5))  # a checker step between shades
            px.putpixel((x, y), shades[k if a >= 200 else len(shades) - 1])
    ey = int(grid * 0.55)
    for ex in (grid // 2 - 4, grid // 2 + 3):  # the eyes
        for dx in (0, 1):
            for dy in (0, 1):
                px.putpixel((ex + dx, ey + dy), (20, 24, 36))
    return px.resize((size, size), Image.NEAREST)

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
