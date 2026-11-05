# Badge and name-strip textures cut from Halicki's straight-on photo (halicki2023_3.jpg,
# CC BY-SA 4.0): python3 textures-make.py (writes badge.jpg, name-strip.jpg, viewfinder.jpg).
import os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
im = Image.open(os.path.join(HERE, "halicki2023_3.jpg")).convert("RGB")
im.crop((445, 415, 720, 645)).save(os.path.join(HERE, "badge.jpg"), quality=92)
im.crop((403, 1252, 1577, 1360)).save(os.path.join(HERE, "name-strip.jpg"), quality=92)
im.crop((1272, 415, 1538, 638)).save(os.path.join(HERE, "viewfinder.jpg"), quality=92)
