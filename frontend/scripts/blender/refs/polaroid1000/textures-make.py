# Badge and name-strip textures cut from Halicki's straight-on photo (halicki2023_3.jpg,
# CC BY-SA 4.0): python3 textures-make.py (writes badge.jpg, name-strip.jpg, viewfinder.jpg).
import os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
im = Image.open(os.path.join(HERE, "halicki2023_3.jpg")).convert("RGB")
im.crop((445, 415, 720, 645)).save(os.path.join(HERE, "badge.jpg"), quality=92)
im.crop((403, 1252, 1577, 1360)).save(os.path.join(HERE, "name-strip.jpg"), quality=92)
im.crop((1272, 415, 1538, 638)).save(os.path.join(HERE, "viewfinder.jpg"), quality=92)

# The print: NASA's AS11-40-5903 (Aldrin on the Moon, Apollo 11; public domain), downloaded from
# https://images-assets.nasa.gov/image/as11-40-5903/as11-40-5903~orig.jpg and passed as the first
# argument: python3 textures-make.py as11-40-5903~orig.jpg (writes print.jpg). Laid out at 10 px/mm
# on the 88 x 107 mm SX-70 print: the 79 x 77 mm picture 4.5 mm in from the sides, 6 mm from the top,
# the wide border (the pod's) below it; the off-white of the border estimated.
import sys
if len(sys.argv) > 1:
    ph = Image.open(sys.argv[1]).convert("RGB")
    pic = ph.crop((700, 60, 4800, 4056)).resize((790, 770), Image.LANCZOS)
    card = Image.new("RGB", (880, 1070), (238, 236, 228))
    card.paste(pic, (45, 60))
    card.save(os.path.join(HERE, "print.jpg"), quality=90)
