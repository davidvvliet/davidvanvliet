# Fit a pinhole camera to a photo of the real vehicle (plain Python 3 with numpy and Pillow; run
# through `run.py photo fit`): landmarks for a start, then the outline (the overlap of the model's
# silhouette with the photo's, the photo's being everything not joined to its border through dark
# pixels, so a photo on a dark background works best).
#
#   photo_fit.py <model.npz> <photo.jpg> <fit.json> <camera.json> <overlay.png>
#
# fit.json (refs/<probe>/photos/<name>.fit.json):
#   "landmarks": [{"object": <part>, "pick": max_x|min_x|top_front|top_rear|tip, "px": [u, v]}
#                 or {"xyz": [x, y, z], "px": [u, v]}, ...]   at least 4, spread over the photo
#   "centre": [x, y, z]   a point the camera looks near (starts), "distance": m (starts, default 25)
#   "scale": 4 (silhouette work at 1/scale size), "dark": 20 (background level 0-255),
#   "exclude": [[x0, y0, x1, y1], ...] photo boxes left out (stands, people, other exhibits),
#   "leave_out": [part name prefixes] not in the silhouette (glass, open hatches),
#   "show": [part names] drawn in red on the overlay, "iters": 250 (outline steps; 0 = landmarks only)
# The camera: "params" [f, rx, ry, rz, tx, ty, tz, cx, cy] (px; camera x right, y down, looking
# along +z; world point p -> R(rx, ry, rz) p + t), and the photo's size. The photo is data: read, never run.
import sys, json, math, numpy as np
from PIL import Image, ImageDraw
model, photo, cfg_path, out_cam, out_overlay = sys.argv[1:6]
cfg = json.load(open(cfg_path))
M = np.load(model)
names = sorted({k.split("|")[0] for k in M.files})
V = {n: M[n + "|v"].astype(float) for n in names}
F = {n: M[n + "|f"] for n in names}
E = {n: M[n + "|e"] for n in names}
im = Image.open(photo).convert("RGB")
W, H = im.size
S = cfg.get("scale", 4)
w, h = W // S, H // S
lum = np.asarray(im.convert("L").resize((w, h), Image.BILINEAR), dtype=float)
# object mask: everything not connected to the border through dark pixels
dark = lum <= cfg.get("dark", 20)
bg = np.zeros_like(dark)
stack = [(0, x) for x in range(w)] + [(h - 1, x) for x in range(w)] + [(y, 0) for y in range(h)] + [(y, w - 1) for y in range(h)]
while stack:
    y, x = stack.pop()
    if 0 <= y < h and 0 <= x < w and dark[y, x] and not bg[y, x]:
        bg[y, x] = True
        stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
obj = ~bg
valid = np.ones_like(obj)
for x0, y0, x1, y1 in cfg.get("exclude", []):
    valid[y0 // S:y1 // S, x0 // S:x1 // S] = False

def rot(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

def look(pos, tgt, roll=0.0):
    """Camera params from a position and target (world), camera y down."""
    pos, tgt = np.array(pos, float), np.array(tgt, float)
    fwd = tgt - pos; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    R = np.array([right, down, fwd])
    return R, -R @ pos

def params_to(p):
    f, rx, ry, rz, tx, ty, tz = p[:7]
    return f, rot(rx, ry, rz), np.array([tx, ty, tz])

def project(p, pts):
    f, R, t = params_to(p)
    cx, cy = (p[7], p[8]) if len(p) > 7 else (0.0, 0.0)  # principal point offset (cropped photos)
    c = pts @ R.T + t
    z = np.maximum(c[:, 2], 1e-3)
    return np.stack([W / 2 + cx + f * c[:, 0] / z, H / 2 + cy + f * c[:, 1] / z], 1), c[:, 2]

def landmark(spec):
    if "xyz" in spec: return np.array(spec["xyz"], float)
    v = V[spec["object"]]
    if spec["pick"] == "max_x": return v[np.argmax(v[:, 0])]
    if spec["pick"] == "min_x": return v[np.argmin(v[:, 0])]
    if spec["pick"] == "top_front": z = v[:, 2].max(); s = v[v[:, 2] > z - 0.01]; return s[np.argmax(s[:, 0])]
    if spec["pick"] == "top_rear": z = v[:, 2].max(); s = v[v[:, 2] > z - 0.01]; return s[np.argmin(s[:, 0])]
    if spec["pick"] == "tip": a = np.abs(v[:, 1]); s = v[a > a.max() - 0.01]; return s.mean(0)
    raise ValueError(spec)

L3 = np.array([landmark(l) for l in cfg["landmarks"]])
L2 = np.array([l["px"] for l in cfg["landmarks"]], float)

def mat_to_euler(R):
    ry = -math.asin(max(-1, min(1, R[2, 0])))
    rx = math.atan2(R[2, 1], R[2, 2]); rz = math.atan2(R[1, 0], R[0, 0])
    return rx, ry, rz

def lm_err(p):
    uv, _ = project(p, L3)
    return (uv - L2).ravel()

def gauss_newton(p, fn, iters=60):
    p = np.array(p, float)
    for _ in range(iters):
        r = fn(p)
        J = np.zeros((len(r), len(p)))
        for i in range(len(p)):
            d = np.zeros(len(p)); d[i] = 1e-4 * max(1.0, abs(p[i]))
            J[:, i] = (fn(p + d) - r) / d[i]
        step = np.linalg.lstsq(J, -r, rcond=None)[0]
        p = p + step
        if np.linalg.norm(step) < 1e-7: break
    return p

best = None
centre = np.array(cfg.get("centre") or np.concatenate([v for v in V.values()]).mean(0))
for az in range(0, 360, 30):
    for el in (-30, -10, 10, 30, 50):
        pos = centre + cfg.get("distance", 25) * np.array([math.cos(math.radians(el)) * math.cos(math.radians(az)),
                                      math.cos(math.radians(el)) * math.sin(math.radians(az)), math.sin(math.radians(el))])
        R, t = look(pos, centre)
        p0 = [W * 1.5, *mat_to_euler(R), *t]
        try:
            p = gauss_newton(p0, lm_err)
        except np.linalg.LinAlgError:
            continue
        uv, z = project(p, L3)
        e = np.sqrt(np.mean(np.sum((uv - L2) ** 2, 1)))
        if (z > 0).all() and p[0] > 0 and (best is None or e < best[0]):
            best = (e, p)
print("landmark rms px", round(best[0], 1), "f px", round(best[1][0]))
p = np.concatenate([best[1], [0.0, 0.0]])

fit_objs = [n for n in names if not any(n.startswith(x) for x in cfg.get("leave_out", []))]

def silhouette(p, objs, scale=S):
    img = Image.new("L", (W // scale, H // scale), 0)
    d = ImageDraw.Draw(img)
    for n in objs:
        uv, z = project(p, V[n])
        uv = uv / scale
        for a, b, c in F[n]:
            d.polygon([tuple(uv[a]), tuple(uv[b]), tuple(uv[c])], fill=255)
    return np.asarray(img) > 0

def cost(p):
    m = silhouette(p, fit_objs)
    inter = (m & obj & valid).sum(); union = ((m | obj) & valid).sum()
    return 1 - inter / union

# Nelder-Mead on the silhouette, steps scaled per parameter
steps = np.array([p[0] * 0.03, 0.02, 0.02, 0.02, 0.2, 0.2, 0.5, 30, 30])
simplex = [p] + [p + np.eye(9)[i] * steps[i] for i in range(9)]
vals = [cost(q) for q in simplex]
print("start 1-IoU", round(vals[0], 4))
for it in range(cfg.get("iters", 250)):
    order = np.argsort(vals); simplex = [simplex[i] for i in order]; vals = [vals[i] for i in order]
    c = np.mean(simplex[:-1], 0)
    xr = c + (c - simplex[-1]); fr = cost(xr)
    if fr < vals[0]:
        xe = c + 2 * (c - simplex[-1]); fe = cost(xe)
        simplex[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
    elif fr < vals[-2]:
        simplex[-1], vals[-1] = xr, fr
    else:
        xc = c + 0.5 * (simplex[-1] - c); fc = cost(xc)
        if fc < vals[-1]:
            simplex[-1], vals[-1] = xc, fc
        else:
            simplex = [simplex[0]] + [simplex[0] + 0.5 * (q - simplex[0]) for q in simplex[1:]]
            vals = [vals[0]] + [cost(q) for q in simplex[1:]]
p = simplex[int(np.argmin(vals))]
print("fitted 1-IoU", round(min(vals), 4), "f px", round(p[0]), "centre offset", np.round(p[7:], 1))
json.dump({"size": [W, H], "params": [float(x) for x in p], "landmark_rms_px": round(float(best[0]), 1),
           "one_minus_iou": round(float(min(vals)), 4) if cfg.get("iters", 250) else None},
          open(out_cam, "w"), indent=1)

# overlay at full resolution: photo outline cyan, model outline (fitted parts) green, `show` parts red
over = im.copy()
d = ImageDraw.Draw(over)
def outline(mask, colour, scale):
    ys, xs = np.nonzero(mask & ~np.roll(mask, 1, 0) | mask & ~np.roll(mask, 1, 1) | mask & ~np.roll(mask, -1, 0) | mask & ~np.roll(mask, -1, 1))
    for y, x in zip(ys, xs):
        d.rectangle([x * scale, y * scale, x * scale + scale - 1, y * scale + scale - 1], fill=colour)
outline(obj, (0, 255, 255), S)
outline(silhouette(p, fit_objs, 2), (0, 255, 0), 2)
for n in cfg.get("show", []):
    uv, _ = project(p, V[n])
    for a, b in E[n]:
        d.line([tuple(uv[a]), tuple(uv[b])], fill=(255, 40, 40), width=2)
over.save(out_overlay)
print("FIT_OK", out_cam)
