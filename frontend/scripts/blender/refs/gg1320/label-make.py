import sys, statistics
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
sx, sy = 512.0, 460.0      # the screw at the label's centre
cx, cy, R = 512.0, 493.5, 507.5  # the label's edge, fitted to rows 100/800
k = R / 32.5               # px per mm (label 65 mm across)
N = 1024
half = 32.5
# label grey: median of plain areas
pts = [(60, 420), (980, 420), (512, 330), (512, 905), (300, 430), (760, 900)]
g = tuple(int(statistics.median(im.getpixel(p)[c] for p in pts)) for c in range(3))
# fill outside the photo's label circle with plain label grey
mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).ellipse((cx - R + 6, cy - R + 6, cx + R - 6, cy + R - 6), fill=255)
base = Image.new("RGB", im.size, g); base.paste(im, (0, 0), mask)
scale = 2 * half * k / N
tex = base.transform((N, N), Image.AFFINE, (scale, 0, sx - half * k, 0, scale, sy - half * k),
                     resample=Image.BICUBIC, fillcolor=g)
# match the label's grey sampled in the overall photos (spec materials.case_label, #484b4d)
target = (0x48, 0x4b, 0x4d)
tex = Image.merge("RGB", [band.point(lambda v, f=target[i] / g[i]: min(255, int(v * f + 0.5)))
                          for i, band in enumerate(tex.split())])
tex.save(out, quality=88)
print("grey", g, "px/mm", round(k, 3))
