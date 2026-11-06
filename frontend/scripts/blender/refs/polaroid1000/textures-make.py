# Badge and name-strip textures cut from Halicki's straight-on photo (halicki2023_3.jpg,
# CC BY-SA 4.0): python3 textures-make.py (writes badge.jpg, name-strip.jpg, viewfinder.jpg).
import os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
im = Image.open(os.path.join(HERE, "halicki2023_3.jpg")).convert("RGB")
im.crop((445, 415, 720, 645)).save(os.path.join(HERE, "badge.jpg"), quality=92)
im.crop((403, 1252, 1577, 1360)).save(os.path.join(HERE, "name-strip.jpg"), quality=92)
im.crop((1272, 415, 1538, 638)).save(os.path.join(HERE, "viewfinder.jpg"), quality=92)

# The print: NASA's AS15-88-11972 (Apollo 15's CSM Endeavour over the Moon, seen from the LM Falcon;
# public domain), the turned and trimmed copy on Wikimedia Commons, downloaded from
# https://upload.wikimedia.org/wikipedia/commons/5/51/Apollo_15_CSM_Endeavour_during_rendezvous.jpg and
# passed as the first argument: python3 textures-make.py Apollo_15_CSM_Endeavour_during_rendezvous.jpg
# (writes print.jpg). Laid out at 10 px/mm on the 88 x 107 mm SX-70 print: the 79 x 77 mm picture 4.5 mm
# in from the sides, 6 mm from the top, the wide border (the pod's) below it; the off-white of the
# border estimated.
import sys
if len(sys.argv) > 1:
    ph = Image.open(sys.argv[1]).convert("RGB")
    pic = ph.crop((0, 20, 1542, 1523)).resize((790, 770), Image.LANCZOS)
    card = Image.new("RGB", (880, 1070), (238, 236, 228))
    card.paste(pic, (45, 60))
    card.save(os.path.join(HERE, "print.jpg"), quality=90)
