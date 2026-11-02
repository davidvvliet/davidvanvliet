# Draws the 16 mm lens's printing as two ring textures (recipe "screens" with "wrap"): the focus ring's
# "10Mega Pixels / 16mm 1:1.4 / FAR ◀ ▶ NEAR" and the aperture scale "1.4 • 2.8 • 5.6 8 16".
#   python3 boards/star-tracker-hat/markings.py
# Text, places and sizes measured off Waveshare's side-on product photo (waveshare.com/16mm-telephoto-lens-for-pi.htm,
# image -1; 14.95 px/mm from the hood's 39 mm): each item's angle from the lock screws' side, asin(x offset / ring
# radius in px), and its height on the ring. The lettering is set in Helvetica, close to the photo's sans serif.
import math, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PX = 40                      # texture pixels per mm
INK, BLACK = (226, 226, 222), (15, 15, 15)   # ink sampled off the photo's letters; black as the model's ("0.06")
FONT = "/System/Library/Fonts/Helvetica.ttc"

def ring(path, diameter, height, items):
    """items: (text, angle_deg, v (0 bottom..1 top, the text's middle), cap height mm, anchor "l", "r" or "m")."""
    w, h = round(math.pi * diameter * PX), round(height * PX)
    img = Image.new("RGB", (w, h), BLACK); d = ImageDraw.Draw(img)
    for text, deg, v, cap, anchor in items:
        x, y = (0.5 + deg / 360) * w, (1 - v) * h
        if text == "•":
            r = 0.25 * PX; d.ellipse([x - r, y - r, x + r, y + r], fill=INK); continue
        if text in "◀▶":   # drawn: the font has no such glyph
            a, k = cap * PX / 2, (-1 if text == "◀" else 1)
            d.polygon([(x + k * a, y), (x - k * a, y - a), (x - k * a, y + a)], fill=INK); continue
        f = ImageFont.truetype(FONT, round(cap * PX / 0.72), index=1)  # bold, as in the photo; capitals are 0.72 of the size
        d.text((x, y), text, font=f, fill=INK, anchor={"l": "lm", "r": "rm", "m": "mm"}[anchor])
    img.save(os.path.join(HERE, path))

# Focus ring: ø35.0, 10.9 high. Left column ends at -7°, right column starts at +10.5°; rows at v 0.76, 0.46, 0.17;
# the arrows' middles at -9.1° and +12.9°, FAR ending at -13.6°, NEAR starting at +16.3°.
ring("lens-focus.png", 35.0, 10.9, [
    ("10Mega", -7, 0.764, 1.45, "r"), ("Pixels", 10.5, 0.764, 1.45, "l"),
    ("16mm", -7, 0.458, 1.45, "r"), ("1:1.4", 10.5, 0.458, 1.45, "l"),
    ("FAR", -13.6, 0.169, 1.3, "r"), ("◀", -9.1, 0.169, 1.1, "m"), ("▶", 12.9, 0.169, 1.1, "m"), ("NEAR", 16.3, 0.169, 1.3, "l")])
# Aperture scale band: ø34.1, 6.2 high; the numbers' middles at v 0.33.
ring("lens-aperture.png", 34.1, 6.2, [
    ("1.4", -12.8, 0.326, 1.15, "m"), ("•", -1.0, 0.326, 0, "m"), ("2.8", 9.1, 0.326, 1.15, "m"),
    ("•", 18.6, 0.326, 0, "m"), ("5.6", 29.9, 0.326, 1.15, "m"), ("8", 43.5, 0.326, 1.15, "m"), ("16", 55.2, 0.326, 1.15, "m")])
