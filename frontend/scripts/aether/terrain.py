# The ground for the Altair Aether launch page (app/models/aether): a patch of the real lunar
# south pole around the mass driver's track, from NASA Goddard's LOLA elevation mosaic, with the
# track's cuts and embankments carved in and the Sun's shadows for the launch date baked in.
#
#   python3 scripts/aether/terrain.py            (from frontend/)
#
# Writes public/models/aether-launch/terrain.json and terrain.bin. Downloads are cached in
# scripts/aether/cache/ (not committed).
#
# Source: "New 5 m/pix LOLA DEM Mosaic for 87 - 90 degrees South", PGDA, NASA Goddard
# (https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/). Barker et al. 2021, Planetary & Space Science 203,
# 105119. 5 m/pix GeoTIFF, south polar stereographic X/Y in metres, MOON_ME frame (DE421), heights in
# metres above the 1737.4 km sphere. We read its 20 m overview, tile by tile (the server refuses fast
# bursts of range requests, so they go one at a time with a pause).
#
# The route and the date were chosen by a search over this map (see README.md) for the first, 17.2 km
# line (to a 673 x 7331 km orbit); the track now ends 12.0 km along it (a 700 km circular orbit). The line
# with the least earthwork whose run-out is clear, on the Earth-facing side of the pole, and the
# hour in the next 400 days with the whole track sunlit and the Earth well above the real horizon.
import json, os, struct, subprocess, sys, time, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(HERE, "cache")
OUT = os.path.join(FRONTEND, "public", "models", "aether-launch")
URL = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/ldem_87s_5mpp.tif"

# --- the launch (the same numbers as AetherLaunch.tsx and specs/aether.json) ---
R = 1737400.0                            # m, the LOLA reference sphere (also the page's R)
GM = 4.9e12
R_A = R + 700e3                          # the shot's high point: the 700 km circular orbit
G0 = 9.80665
ACC = 14 * G0
V = (2 * GM * R_A / (R * (R + R_A))) ** 0.5
L = V * V / (2 * ACC)                    # track length, 12.0 km
START = (16040.0, 6040.0)                # m, polar stereographic: where the track begins
HEADING = 145.0                          # deg, in the stereographic plane, counter-clockwise from +x
JD = 2461773.125                         # 2028-01-02 15:00 UTC: the track sunlit, the Earth up and 73 % lit (spec launch_date)
G_BEND = 1.0 * G0                        # design: the track's bends add at most 1 g
DECK = 5.0                               # m, half-width of the flat track bed
SIDE = 0.7                               # cut and fill slopes (35 degrees)

# --- the elevation mosaic: 20 m overview (level 2), 10000 x 10000 px from (-100 km, +100 km) ---
PX, X0M, Y0M = 20.0, -100000.0, 100000.0

def fetch(col0, row0, w, h):
    path = os.path.join(CACHE, f"ldem20_{col0}_{row0}_{w}_{h}.npy")
    if os.path.exists(path):
        return np.load(path)
    # A larger window fetched before covers this one: cut it out.
    for name in sorted(os.listdir(CACHE)) if os.path.isdir(CACHE) else []:
        try:
            c, r, ww, hh = (int(x) for x in name[len("ldem20_"):-len(".npy")].split("_"))
        except ValueError:
            continue
        if c <= col0 and r <= row0 and c + ww >= col0 + w and r + hh >= row0 + h:
            return np.load(os.path.join(CACHE, name))[row0 - r:row0 - r + h, col0 - c:col0 - c + w]
    os.makedirs(CACHE, exist_ok=True)
    def get(a, n):
        for k in range(10):
            r = subprocess.run(["curl", "-s", "-f", "-r", f"{a}-{a + n - 1}", URL], capture_output=True)
            if r.returncode == 0 and len(r.stdout) == n:
                time.sleep(0.4)
                return r.stdout
            time.sleep(3 * (k + 1))
        sys.exit(f"download failed: bytes {a}+{n}")
    hd = get(0, 16)
    E = "<" if hd[:2] == b"II" else ">"
    big = struct.unpack(E + "H", hd[2:4])[0] == 43
    off = struct.unpack(E + ("Q" if big else "I"), hd[8:16] if big else hd[4:8])[0]
    def entries(off):
        if big:
            n = struct.unpack(E + "Q", get(off, 8))[0]; return n, get(off + 8, n * 20 + 8), 20
        n = struct.unpack(E + "H", get(off, 2))[0]; return n, get(off + 2, n * 12 + 4), 12
    for _ in range(2):                    # skip the full image and the 10 m overview
        n, ent, esz = entries(off)
        off = struct.unpack(E + ("Q" if big else "I"), ent[n * esz:n * esz + (8 if big else 4)])[0]
    n, ent, esz = entries(off)
    types = {3: ("H", 2), 4: ("I", 4), 16: ("Q", 8)}
    tags = {}
    for i in range(n):
        e = ent[i * esz:(i + 1) * esz]
        tag, typ, cnt = struct.unpack(E + ("HHQ" if big else "HHI"), e[:12] if big else e[:8])
        val = e[12:20] if big else e[8:12]
        if typ not in types: continue
        f, sz = types[typ]
        data = val[:cnt * sz] if cnt * sz <= len(val) else get(struct.unpack(E + ("Q" if big else "I"), val)[0], cnt * sz)
        tags[tag] = struct.unpack(E + f * cnt, data)
    W, tw, th = tags[256][0], tags[322][0], tags[323][0]
    assert tags[259][0] == 8 and tags[317][0] == 3, "expected deflate with the floating-point predictor"
    offs, cnts, tx = tags[324], tags[325], (W + tw - 1) // tw
    res = np.full((h, w), np.nan, np.float32)
    for ty in range(row0 // th, (row0 + h - 1) // th + 1):
        cols = list(range(col0 // tw, (col0 + w - 1) // tw + 1))
        ids = [ty * tx + c for c in cols]
        a = min(offs[i] for i in ids); b = max(offs[i] + cnts[i] for i in ids)
        blob = get(a, b - a)
        for c, i in zip(cols, ids):
            d = np.frombuffer(zlib.decompress(blob[offs[i] - a:offs[i] - a + cnts[i]]), np.uint8).reshape(th, tw * 4)
            d = np.cumsum(d, axis=1, dtype=np.uint8).reshape(th, 4, tw).transpose(0, 2, 1)   # undo the predictor
            t = np.ascontiguousarray(d).view(">f4").reshape(th, tw).astype(np.float32)
            gx, gy = c * tw, ty * th
            x0, y0, x1, y1 = max(gx, col0), max(gy, row0), min(gx + tw, col0 + w), min(gy + th, row0 + h)
            res[y0 - row0:y1 - row0, x0 - col0:x1 - col0] = t[y0 - gy:y1 - gy, x0 - gx:x1 - gx]
        print(f"  tile row {ty}", end="\r", file=sys.stderr)
    np.save(path, res)
    return res

def fixed(x, y):
    """Polar stereographic (south, true scale at the pole) -> unit vector in the Moon's body-fixed frame."""
    rho = np.hypot(x, y); lat = 2 * np.arctan(rho / (2 * R)) - np.pi / 2; lon = np.arctan2(x, y)
    return np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], -1)

def main():
    c, sn = np.cos(np.radians(HEADING)), np.sin(np.radians(HEADING))
    fwd, left = np.array([c, sn]), np.array([-sn, c])          # +90 in the plane is the track's left

    # Mesh grid along (u) and across (v) the track: fine near it, stretching out to the horizon.
    def axis(fine, step, out, ratio):
        a = list(np.arange(fine[0], fine[1] + 1e-6, step))
        lo, hi, s = a[0], a[-1], step
        while lo > out[0] or hi < out[1]:
            s *= ratio
            if lo > out[0]: lo -= s; a.insert(0, lo)
            if hi < out[1]: hi += s; a.append(hi)
        return np.array(a)
    u = axis((-1500.0, L + 14000.0), 40.0, (-10000.0, L + 30000.0), 1.15)
    # Columns exactly at both ends of the track, and 2.5 m apart just past them, so the cutting ends in a wall
    # (on 40 m columns the wall would be smeared over the first 20 m of the track).
    ends = np.r_[np.arange(-40.0, 0.01, 2.5), L + np.arange(0.0, 40.01, 2.5)]
    u = np.union1d(u[np.min(np.abs(u[:, None] - ends[None, :]), axis=1) > 1.0], ends)
    vs = [0.0]
    for lim, step in [(10, 2.5), (60, 5.0), (300, 20.0), (1500, 40.0)]:
        while vs[-1] + step <= lim + 1e-6: vs.append(vs[-1] + step)
    s_ = 40.0
    while vs[-1] < 25000: s_ *= 1.15; vs.append(vs[-1] + s_)
    v = np.array([-x for x in vs[:0:-1]] + vs)
    print(f"grid {len(u)} x {len(v)} = {len(u) * len(v)} vertices", file=sys.stderr)

    # Fetch the bounding box of the mesh plus 10 km on every side (shadows cast from beyond it are ignored).
    U, Vv = np.meshgrid(u, v)
    gx = START[0] + U * fwd[0] + Vv * left[0]; gy = START[1] + U * fwd[1] + Vv * left[1]
    xmin, xmax = max(gx.min() - 10000, X0M), min(gx.max() + 10000, -X0M - PX)
    ymin, ymax = max(gy.min() - 10000, -Y0M + PX), min(gy.max() + 10000, Y0M)
    col0, row0 = int((xmin - X0M) // PX), int((Y0M - ymax) // PX)
    w, h = int((xmax - xmin) // PX), int((ymax - ymin) // PX)
    print(f"fetching {w} x {h} px at 20 m", file=sys.stderr)
    Z = fetch(col0, row0, w, h)
    zx0, zy0 = X0M + col0 * PX, Y0M - row0 * PX
    def samp(x, y):
        cc = np.clip((x - zx0) / PX, 0, w - 1.001); rr = np.clip((zy0 - y) / PX, 0, h - 1.001)
        c0, r0 = cc.astype(int), rr.astype(int); fc, fr = cc - c0, rr - r0
        out = (Z[r0, c0] * (1 - fc) * (1 - fr) + Z[r0, c0 + 1] * fc * (1 - fr) + Z[r0 + 1, c0] * (1 - fc) * fr + Z[r0 + 1, c0 + 1] * fc * fr)
        return np.where(np.isnan(out), -1e4, out)

    # The track's profile: as close to the ground as the bends allow at each speed, and level at the end.
    ds = 50.0
    s = np.arange(0, L + 1e-6, ds); s[-1] = L; n = len(s)
    zz = samp(START[0] + s * fwd[0], START[1] + s * fwd[1])
    v2 = 2 * ACC * np.maximum(s, ds)
    D = np.zeros((n - 2, n))
    for i in range(n - 2): D[i, i:i + 3] = [1, -2, 1]
    Ee = np.zeros((1, n)); Ee[0, -2:] = [-1, 1]
    for lam in 10 ** np.arange(6, 12.01, 0.25):
        wgt = lam * (v2[1:-1] / v2[-1]) ** 2
        p = np.linalg.solve(np.eye(n) + D.T @ (wgt[:, None] * D) + lam * Ee.T @ Ee, zz)
        if ((np.abs(D @ p) / ds ** 2) * v2[1:-1]).max() <= G_BEND: break
    print(f"track: {p[0]:.0f} m to {p[-1]:.0f} m; deepest cut {(zz - p).max():.0f} m, highest fill {(p - zz).max():.0f} m", file=sys.stderr)

    def ground(x, y):
        """Terrain height with the track bed carved in: flat across the bed, 35-degree cuts and fills beside it."""
        z = samp(x, y)
        du, dv = (x - START[0]) * fwd[0] + (y - START[1]) * fwd[1], (x - START[0]) * left[0] + (y - START[1]) * left[1]
        pt = np.interp(np.clip(du, 0, L), s, p)
        d = np.hypot(np.maximum(0, np.abs(dv) - DECK), np.maximum(0, np.maximum(-du, du - L)))
        return np.clip(z, pt - SIDE * d, pt + SIDE * d)

    zg = ground(gx, gy)

    # Sunlight at the launch date: the Sun's direction from sky.ts (the page's own code).
    sun = np.array(json.loads(subprocess.run(["npx", "-y", "tsx", os.path.join(HERE, "sun.ts"), str(JD)],
                                             cwd=FRONTEND, capture_output=True, text=True, check=True).stdout))
    sun /= np.linalg.norm(sun)
    Pn = fixed(gx, gy)
    el = np.degrees(np.arcsin(Pn @ sun))
    # The Sun's direction in the stereographic plane at each vertex.
    ex, ny = fixed(gx + 1, gy) - Pn, fixed(gx, gy + 1) - Pn
    uh = sun - (Pn @ sun)[..., None] * Pn
    dx, dy = (uh * ex).sum(-1) / (ex * ex).sum(-1), (uh * ny).sum(-1) / (ny * ny).sum(-1)
    nrm = np.hypot(dx, dy); dx, dy = dx / nrm, dy / nrm
    steps = np.cumsum(10.0 * 1.04 ** np.arange(140))           # 10 m, growing to ~60 km
    horizon = np.full(gx.shape, -90.0)
    z0 = zg + 0.5
    for d in steps:
        xs, ys = gx + dx * d, gy + dy * d
        ok = (xs > zx0) & (xs < zx0 + w * PX) & (ys < zy0) & (ys > zy0 - h * PX)
        a = np.degrees(np.arctan2(ground(xs, ys) - z0, d) - d / (2 * R))
        horizon = np.where(ok, np.maximum(horizon, a), horizon)
    sunlit = np.clip((el - horizon) / 0.53 + 0.5, 0, 1)        # the Sun's disc is about half a degree across
    print(f"sun elevation {el.min():.2f} to {el.max():.2f} deg; sunlit {100 * (sunlit > 0.5).mean():.0f}% of vertices", file=sys.stderr)

    os.makedirs(OUT, exist_ok=True)
    zmin = float(np.floor(zg.min())); zstep = 0.1
    q = np.round((zg - zmin) / zstep)
    assert q.max() < 65536
    with open(os.path.join(OUT, "terrain.bin"), "wb") as f:
        f.write(q.astype("<u2").tobytes()); f.write(np.round(sunlit * 255).astype(np.uint8).tobytes())
    meta = {
        "about": "Lunar south pole around the Altair Aether track: LOLA 87S mosaic (NASA Goddard PGDA, Barker et al. 2021), 20 m overview. Built by scripts/aether/terrain.py.",
        "R": R, "jd": JD, "start": START, "heading": HEADING, "length": L,
        "profile": {"ds": ds, "z": [round(float(x), 2) for x in p]},
        "u": [round(float(x), 1) for x in u], "v": [round(float(x), 2) for x in v],
        "zmin": zmin, "zstep": zstep,
    }
    with open(os.path.join(OUT, "terrain.json"), "w") as f: json.dump(meta, f, separators=(",", ":"))
    print(f"wrote {OUT}: {os.path.getsize(os.path.join(OUT, 'terrain.bin')) // 1024} KB", file=sys.stderr)

if __name__ == "__main__":
    main()
