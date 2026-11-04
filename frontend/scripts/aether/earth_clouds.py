# The Earth for the Aether launch page (public/models/aether-launch/earth.jpg): the clouds of NASA SVS 3615
# ("Equirectangular Projected Earth for LARGEST", https://svs.gsfc.nasa.gov/3615/; the same frame with and
# without clouds, so the clouds are what brightened), laid over NASA's January Blue Marble Next Generation map.
#   python3 scripts/aether/earth_clouds.py <dir with dl/still.jpg and dl/noclouds.jpg> <blue marble 2048x1024 jpg>
# (SVS 3615's flat_earth_Largest_still.0330.jpg and earth_noClouds.0330.jpg.) Writes <dir>/earth-clouds.jpg.
import sys, numpy as np
from PIL import Image
D = sys.argv[1]; BM = sys.argv[2]
still = np.asarray(Image.open(f"{D}/dl/still.jpg").resize((2048, 1024), Image.LANCZOS), np.float32)
none = np.asarray(Image.open(f"{D}/dl/noclouds.jpg").resize((2048, 1024), Image.LANCZOS), np.float32)
lum = lambda a: a @ np.array([0.299, 0.587, 0.114], np.float32)
ls, ln = lum(still), lum(none)
a = np.clip((ls - ln) / np.maximum(255 - ln, 1), 0, 1)       # how far each pixel went toward white
a = np.clip((a - 0.04) / 0.96, 0, 1)                           # drop the faint haze
bm = np.asarray(Image.open(BM).convert("RGB"), np.float32)
out = bm * (1 - a[..., None]) + 245.0 * a[..., None]
Image.fromarray(out.astype(np.uint8)).save(f"{D}/earth-clouds.jpg", quality=88)
print("cloud cover", round(float(a.mean()), 3))
