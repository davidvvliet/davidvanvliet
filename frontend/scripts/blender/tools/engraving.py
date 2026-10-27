#!/usr/bin/env python3
# Turns a line drawing of an engraved plate into the line image a probe's textures are made
# from, laid out like a photo of the real plate. Plain Python 3 + numpy + Pillow; renders SVG
# with macOS Quick Look (qlmanage), which maps a square SVG viewBox exactly onto the image.
#
#   engraving.py fit <drawing.svg> <photo> <fit.json> --groups A,B,...
#       Finds the plate's rim in the photo, then places each named SVG group (scale +
#       offset) where its lines best overlap the photo's engraved lines. Groups left out
#       (labels, arrows) are dropped.
#   engraving.py lines <drawing.svg> <fit.json> <lines.png> [--px 2048]
#       Renders the fitted groups into a square image spanning the plate's diameter
#       (white = engraved), the layout the disc part's UVs expect.
#   engraving.py overlay <drawing.svg> <photo> <fit.json> <overlay.png>
#       The fitted lines in cyan over the photo, to check the fit by eye.
#
# Inputs are data (downloaded drawings and photos); nothing in them is executed.
import json, os, subprocess, sys, tempfile, xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)

def _groups(svg_path):
    root = ET.parse(svg_path).getroot()
    vb = [float(v) for v in root.get("viewBox").split()]
    return {g.get("id"): g for g in root if g.tag == f"{{{NS}}}g"}, vb

def _render(groups, transforms, size):
    """White image of `size` px with each group drawn through its matrix (svg units -> px)."""
    out = [f'<svg xmlns="{NS}" viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
           f'<rect width="{size}" height="{size}" fill="#fff"/>']
    for gid, (s, tx, ty) in transforms.items():
        out.append(f'<g transform="matrix({s} 0 0 {s} {tx} {ty})">{ET.tostring(groups[gid], encoding="unicode")}</g>')
    out.append("</svg>")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "drawing.svg")
        open(p, "w").write("\n".join(out))
        subprocess.run(["qlmanage", "-t", "-s", str(size), "-o", d, p], capture_output=True, check=True)
        return np.array(Image.open(p + ".png").convert("L"), dtype=np.float32) / 255

def _box_blur(a, r):
    c = np.cumsum(np.cumsum(np.pad(a, ((r + 1, r), (r + 1, r)), mode="edge"), 0), 1)
    k = 2 * r + 1
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)

def _rim(ph):
    """Plate rim: parts of a plate can be as dark as the background, so walk rays in from the
    image edge to the first bright pixel, then least-squares fit a circle (twice, dropping the
    worst fifth, e.g. a lens flare)."""
    H, W = ph.shape
    bl = _box_blur(ph, 4)
    pts = []
    for a in np.linspace(0, 2 * np.pi, 360, endpoint=False):
        for r in np.arange(min(H, W) / 2 - 2, 0, -1):
            x, y = int(W / 2 + r * np.cos(a)), int(H / 2 + r * np.sin(a))
            if bl[y, x] > 0.08:
                pts.append((x, y))
                break
    E = np.array(pts, dtype=float)
    A = np.c_[2 * E, np.ones(len(E))]
    b = (E ** 2).sum(1)
    keep = np.ones(len(E), bool)
    for _ in range(2):
        cx, cy, c = np.linalg.lstsq(A[keep], b[keep], rcond=None)[0]
        R = np.sqrt(c + cx ** 2 + cy ** 2)
        res = np.abs(np.hypot(E[:, 0] - cx, E[:, 1] - cy) - R)
        keep = res <= np.percentile(res, 80)
    return float(cx), float(cy), float(R)

def fit(svg_path, photo_path, out_json, group_ids):
    groups, vb = _groups(svg_path)
    ph = np.array(Image.open(photo_path).convert("L"), dtype=np.float32) / 255
    H, W = ph.shape
    cx, cy, R = _rim(ph)
    # Engraved lines: thin and brighter than the shading around them.
    tophat = np.clip(ph - _box_blur(ph, 12), 0, None)
    yy, xx = np.mgrid[0:H, 0:W]
    inside = (xx - cx) ** 2 + (yy - cy) ** 2 < (R * 0.97) ** 2
    M = np.where(inside, np.clip(tophat / np.percentile(tophat[inside], 97), 0, 1.5), 0)
    M = _box_blur(M, 2)
    # Line points of each group in svg units (rendered at 2 px per unit).
    side = max(vb[2], vb[3])
    px = int(side * 2)
    pts = {}
    for gid in group_ids:
        img = _render(groups, {gid: (2, -vb[0] * 2, -vb[1] * 2)}, px)
        y, x = np.nonzero(img < 0.5)
        pts[gid] = np.stack([x / 2 + vb[0], y / 2 + vb[1]], 1)
    def score(p, s, tx, ty):
        x = (p[:, 0] * s + tx).astype(int); y = (p[:, 1] * s + ty).astype(int)
        ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
        return float(M[y[ok], x[ok]].sum() / len(p))
    def refine(p, start, ds, dt, steps):
        best = (score(p, *start), start)
        for _ in range(steps):
            s0, x0, y0 = best[1]
            for s in np.linspace(s0 - ds, s0 + ds, 9):
                for tx in np.linspace(x0 - dt, x0 + dt, 13):
                    for ty in np.linspace(y0 - dt, y0 + dt, 13):
                        v = score(p, s, tx, ty)
                        if v > best[0]:
                            best = (v, (float(s), float(tx), float(ty)))
            ds, dt = ds / 3, dt / 3
        return best
    # Whole drawing first (coarse grid scaled to the rim), then each group on its own.
    allp = np.concatenate(list(pts.values()))[::4]
    s_guess = 2 * R / side  # drawing as wide as the plate; real drawings are often smaller
    best = (-1, None)
    for s in np.linspace(s_guess * 0.8, s_guess * 2.0, 41):
        for tx in np.arange(-W, W, 16):
            for ty in np.arange(-H, H, 16):
                v = score(allp, s, tx, ty)
                if v > best[0]:
                    best = (v, (float(s), float(tx), float(ty)))
    whole = refine(allp, best[1], s_guess * 0.03, 16, 3)
    fits = {}
    for gid in group_ids:
        g = refine(pts[gid], whole[1], whole[1][0] * 0.06, R * 0.06, 4)
        fits[gid] = {"s": g[1][0], "tx": g[1][1], "ty": g[1][2], "score": round(g[0], 3),
                     "score_whole_drawing_fit": round(score(pts[gid], *whole[1]), 3)}
    json.dump({"drawing": os.path.basename(svg_path), "photo": os.path.basename(photo_path),
               "photo_px": [W, H], "rim": {"cx": cx, "cy": cy, "r": R},
               "note": "per group: photo_px = svg_units * s + (tx, ty); score = mean line strength "
                       "under the group's lines (higher is better)",
               "groups": fits}, open(out_json, "w"), indent=1)
    for gid, f in fits.items():
        print(f"  {gid:<36} score {f['score_whole_drawing_fit']:.2f} -> {f['score']:.2f}")

def _plate_transforms(fitd, k, ox, oy):
    return {g: (f["s"] * k, (f["tx"] - ox) * k, (f["ty"] - oy) * k) for g, f in fitd["groups"].items()}

def lines(svg_path, fit_json, out_png, px=2048):
    groups, _ = _groups(svg_path)
    f = json.load(open(fit_json))
    cx, cy, R = f["rim"]["cx"], f["rim"]["cy"], f["rim"]["r"]
    img = _render(groups, _plate_transforms(f, px / (2 * R), cx - R, cy - R), px)
    Image.fromarray(((1 - img) * 255).astype(np.uint8)).save(out_png)

def overlay(svg_path, photo_path, fit_json, out_png):
    groups, _ = _groups(svg_path)
    f = json.load(open(fit_json))
    ph = Image.open(photo_path).convert("RGB")
    img = _render(groups, _plate_transforms(f, 1.0, 0, 0), ph.size[0])
    o = np.array(ph)
    o[img < 0.5] = (0, 255, 255)
    Image.fromarray(o).save(out_png)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["fit"] and "--groups" in a:
        fit(a[1], a[2], a[3], a[a.index("--groups") + 1].split(","))
    elif a[:1] == ["lines"]:
        lines(a[1], a[2], a[3], int(a[a.index("--px") + 1]) if "--px" in a else 2048)
    elif a[:1] == ["overlay"]:
        overlay(a[1], a[2], a[3], a[4])
    else:
        sys.exit(__doc__ if False else open(__file__).read().split("import json")[0])
