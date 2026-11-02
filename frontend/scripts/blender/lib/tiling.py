# Repeating surface textures (hexagonal heat-shield tiles, weld lines on steel rings) and the
# UVs that wrap them round a body of revolution. Images made here are marked "tiling", so
# checks.textures lets their UVs run past [0, 1].
import math, os
import bpy
import numpy as np

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def srgb(hexstr):
    h = hexstr.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

def image(probe, name, rgb, colorspace):
    """Save rgb (rows bottom-up, values as stored) to out/<probe>/textures/<name>.jpg as a
    JPEG the export keeps as JPEG, marked as a repeating pattern."""
    out = os.path.join(HARNESS, "out", probe, "textures")
    os.makedirs(out, exist_ok=True)
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.concatenate([rgb, np.ones((h, w, 1), np.float32)], 2).ravel())
    img.filepath_raw = os.path.join(out, f"{name}.jpg")
    img.file_format = "JPEG"
    bpy.context.scene.render.image_settings.quality = 90
    img.save()
    img["tiling"] = True
    return img

def hex_tiles(probe, t, tile_hex, repeat_w, cols=4, rows=4, px_per_m=480):
    """Colour and normal map of hexagonal tiles in staggered horizontal rows (vertices up),
    `repeat_w` wide (`cols` tiles) and `rows` rows tall (even), so it repeats seamlessly; every
    tile in the repeat gets its own shade and tilt. `t`: gap, gap_brightness, shade_spread,
    bevel, gap_depth, tilt. Tile centres sit at (m d + (k % 2) d / 2, k d sqrt(3) / 2) in
    texture metres (d = across flats). Returns (base, normal, height)."""
    d = repeat_w / cols                                # across flats = centre spacing in a row
    H = rows * d * math.sqrt(3) / 2
    w, h = int(round(repeat_w * px_per_m)), int(round(H * px_per_m))
    x = (np.arange(w) + 0.5) / w * repeat_w
    y = (np.arange(h) + 0.5) / h * H
    X, Y = np.meshgrid(x.astype(np.float32), y.astype(np.float32))
    # The two nearest tile centres per pixel, from the few candidates around it: rows just
    # below and above, and in each row the nearest centre and its neighbours.
    row = d * math.sqrt(3) / 2
    k0 = np.floor(Y / row).astype(np.int32)
    D2s, idss = [], []
    for dk in (-1, 0, 1, 2):
        k = k0 + dk
        off = (k % 2) * d / 2
        mc = np.rint((X - off) / d).astype(np.int32)
        for dm in (-1, 0, 1):
            m = mc + dm
            D2s.append((X - (m * d + off)) ** 2 + (Y - k * row) ** 2)
            idss.append((m % cols) * rows + (k % rows))
    D2, ids_px = np.stack(D2s, 2), np.stack(idss, 2)
    order = np.argsort(D2, axis=2)[..., :2]
    d1 = np.take_along_axis(D2, order[..., :1], 2)[..., 0]
    d2 = np.take_along_axis(D2, order[..., 1:2], 2)[..., 0]
    cell = np.take_along_axis(ids_px, order[..., :1], 2)[..., 0]
    edge = (d2 - d1) / (2 * d)                         # distance to the cell's edge (m)
    inside = np.clip((edge - t["gap"] / 2) / 0.004, 0, 1)
    # Bevel: each tile's edge rounds down into the gap over `bevel`, so light draws a thin
    # highlight and shadow round every tile.
    bev = np.clip((edge - t["gap"] / 2) / t["bevel"], 0, 1)
    bev = bev * bev * (3 - 2 * bev)
    rng = np.random.default_rng(39)
    shade = 1 + t["shade_spread"] * rng.uniform(-1, 1, cols * rows)
    tilt = rng.uniform(-1, 1, (cols * rows, 2)) * t["tilt"]     # each tile sits slightly off flush
    tile = srgb(tile_hex)[None, None] * shade[cell][..., None]
    gap = srgb(tile_hex) * t["gap_brightness"]
    rgb = tile * inside[..., None] + gap[None, None] * (1 - inside[..., None])
    hgt = -(1 - bev) * t["gap_depth"]                 # gaps sit below the tile faces
    step = repeat_w / w
    dy, dx = np.gradient(hgt, step)
    tl = tilt[cell] * bev[..., None]
    n = np.stack([-dx + tl[..., 0], -dy + tl[..., 1], np.ones_like(hgt)], 2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return (image(probe, "heat_shield_tiles_base", np.clip(rgb, 0, 1).astype(np.float32), "sRGB"),
            image(probe, "heat_shield_tiles_normal", (n * 0.5 + 0.5).astype(np.float32), "Non-Color"),
            H)

def weld_lines(probe, steel_hex, ring_h, line, darken, rings=1, shade_spread=0.0, px_per_m=280):
    """Steel with a darker weld line every `ring_h` metres (u doesn't matter: 8 px wide).
    With `rings` > 1 the image is that many rings tall and each ring's brightness is varied by
    up to `shade_spread` (rings are rolled from different sheets), so map v over rings x ring_h."""
    h = int(round(ring_h * px_per_m))
    v = (np.arange(h) + 0.5) / h * ring_h
    dist = np.minimum(v, ring_h - v)
    k = np.clip(dist / (line / 2), 0, 1)
    shade = darken + (1 - darken) * k
    if rings > 1:
        rng = np.random.default_rng(19)
        shade = np.concatenate([shade * (1 + shade_spread * rng.uniform(-1, 1)) for _ in range(rings)])
    rgb = srgb(steel_hex)[None, None] * shade[:, None, None] * np.ones((1, 8, 1))
    return image(probe, "stainless_steel_welds", np.clip(rgb, 0, 1).astype(np.float32), "sRGB")

def cyl_uv(obj, repeat_w, repeat_h, R):
    """UVs that wrap round the z axis: u = angle x R / repeat_w (the same at every height, so
    a whole number of repeats goes round and there is no seam), v = z / repeat_h."""
    me, mw = obj.data, obj.matrix_world
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        c = mw @ poly.center
        ac = math.atan2(c.y, c.x)
        for li in poly.loop_indices:
            p = mw @ me.vertices[me.loops[li].vertex_index].co
            a = math.atan2(p.y, p.x) if math.hypot(p.x, p.y) > 1e-6 else ac
            a = ac + ((a - ac + math.pi) % (2 * math.pi) - math.pi)
            uv.data[li].uv = (a * R / repeat_w, p.z / repeat_h)

def plane_uv(obj, across, repeat_w, repeat_h):
    """UVs for a flat part: u along the world direction `across`, v = z."""
    me, mw = obj.data, obj.matrix_world
    uv = me.uv_layers.new(name="UVMap")
    for li, loop in enumerate(me.loops):
        p = mw @ me.vertices[loop.vertex_index].co
        uv.data[li].uv = ((p.x * across[0] + p.y * across[1]) / repeat_w, p.z / repeat_h)

def box_uv(obj, repeat):
    """UVs for any shape (a copied mesh, a box): each face is projected onto the world plane it
    faces most, `repeat` metres per tile. Seams fall where faces turn by about 90 degrees, where
    a blanket's fold would be anyway."""
    me, mw = obj.data, obj.matrix_world
    n3 = mw.to_3x3()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = n3 @ poly.normal
        k = max(range(3), key=lambda i: abs(n[i]))
        a, b = [i for i in range(3) if i != k]
        for li in poly.loop_indices:
            q = mw @ me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (q[a] / repeat, q[b] / repeat)

def tube_wall(probe, name, tube_hex, per_tile, split=0.5, px_per_tube=32, h=512, groove=0.5,
              soot=None, rays=None):
    """Colour and normal map of a tube-wall nozzle (tubes along v, side by side across u):
    `per_tile` tubes across the image above v = `split`, twice as many below it (where each
    tube splits in two, as on the F-1 below its 3:1 plane). Repeats across u only. Optional
    for a coated inside: soot {hex, from, to} darkens it towards the throat (v from `from` to
    `to`), rays {hex, from, width} draws one light streak per tile (the "star" seen down a
    nozzle) from v = `from` to the throat, `width` a fraction of the tile. Returns (base, normal)."""
    w = per_tile * px_per_tube
    u = (np.arange(w) + 0.5) / w
    v = (np.arange(h) + 0.5) / h
    U, V = np.meshgrid(u, v)
    n = np.where(V < split, 2 * per_tile, per_tile)
    x = (U * n) % 1.0 * 2 - 1                          # -1..1 across each tube
    hgt = np.sqrt(np.clip(1 - x * x, 0, 1))
    shade = groove + (1 - groove) * hgt ** (0.5 if groove >= 0.5 else 0.25)   # dark in the grooves
    col = np.broadcast_to(srgb(tube_hex)[None, None], V.shape + (3,)).copy()
    if soot:
        t = np.clip((V - soot["from"]) / (soot["to"] - soot["from"]), 0, 1)
        t = (t * t * (3 - 2 * t))[..., None]
        col = col * (1 - t) + srgb(soot["hex"])[None, None] * t
    if rays:
        d = np.minimum(np.abs(U - 0.5), 1 - np.abs(U - 0.5))      # distance from the tile's middle
        m = np.exp(-(d / (rays["width"] / 2)) ** 2)
        m = m * np.clip((V - rays["from"]) / max(1e-6, 1 - rays["from"]), 0, 1) ** 0.7
        col = col * (1 - m[..., None]) + srgb(rays["hex"])[None, None] * m[..., None]
    rgb = col * shade[..., None]
    dx = np.where(np.abs(x) < 0.999, -x / np.maximum(hgt, 0.05), 0) * 0.6
    nrm = np.stack([-dx, np.zeros_like(dx), np.ones_like(dx)], 2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return (image(probe, f"{name}_base", np.clip(rgb, 0, 1).astype(np.float32), "sRGB"),
            image(probe, f"{name}_normal", (nrm * 0.5 + 0.5).astype(np.float32), "Non-Color"))

def _noise(h, w, size_v, size_u, seed):
    """Seamless smooth noise in [-1, 1]: white noise low-passed in the frequency domain, so
    it wraps at the edges. `size_u`, `size_v`: blob size in pixels across and along."""
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None] * size_v
    fx = np.fft.fftfreq(w)[None, :] * size_u
    n = np.real(np.fft.ifft2(f * np.exp(-(fx * fx + fy * fy) * 8)))
    n -= n.mean()
    return n / (np.abs(n).max() + 1e-9)

def _blur_wrap(a, sigma_px):
    """Gaussian blur that wraps at the edges (keeps a repeating image seamless)."""
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.fftfreq(a.shape[1])[None, :]
    g = np.exp(-2 * (np.pi * sigma_px) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))

def mottle(probe, name, base_hex, spread=0.12, blob=(0.25, 0.25), streak=None, patches=None,
           repeat=(0.5, 0.5), px=256, seed=1):
    """Colour map of a mottled finish (heat tint, cast metal, weathered paint), `repeat` metres
    wide and tall: the base colour brightened and darkened by up to `spread` in blobs `blob`
    metres across (u, v); `streak` {spread, length}: extra streaks `length` metres long along v
    (heat tint running down a nozzle); `patches` {hex, cover, blob}: a second colour over about
    `cover` of the surface in blobs (paint worn through to the metal). Returns base."""
    w = px
    h = max(8, int(round(px * repeat[1] / repeat[0])))
    mpp = repeat[0] / w                                  # metres per pixel
    n = _noise(h, w, blob[1] / mpp, blob[0] / mpp, seed)
    n += 0.35 * _noise(h, w, blob[1] / mpp / 4, blob[0] / mpp / 4, seed + 1)   # finer grain
    col = srgb(base_hex)[None, None] * (1 + spread * n)[..., None]
    if streak:
        s = _noise(h, w, streak["length"] / mpp, 0.01 / mpp, seed + 2)
        col = col * (1 + streak["spread"] * s)[..., None]
    if patches:
        m = _noise(h, w, patches["blob"] / mpp, patches["blob"] / mpp, seed + 3)
        t = np.quantile(m, 1 - patches["cover"])
        a = np.clip((m - t) / 0.08, 0, 1)[..., None]
        col = col * (1 - a) + srgb(patches["hex"])[None, None] * a
    return image(probe, f"{name}_base", np.clip(col, 0, 1).astype(np.float32), "sRGB")

def braid(probe, name, base_hex, carriers=6, groove=0.45, px=128):
    """Colour and normal map of a braided hose sheath: two sets of `carriers` strand bands
    winding opposite ways, over two, under two, one tile round the hose and one pitch along.
    Returns (base, normal)."""
    u = (np.arange(px) + 0.5) / px
    U, V = np.meshgrid(u, u)
    a = (U + V) * carriers % 1.0                         # position across a band, one way
    b = (U - V) * carriers % 1.0                         # and the other way
    ia = np.floor((U + V) * carriers).astype(int)
    ib = np.floor((U - V) * carriers).astype(int)
    over = ((ia + ib) // 2) % 2 == 0                     # which band is on top here
    pa = np.sin(np.pi * a) ** 0.6
    pb = np.sin(np.pi * b) ** 0.6
    hgt = np.where(over, pa, pb * 0.8)
    # strand lines within a band (the wires of each carrier)
    fine = np.where(over, np.abs(np.sin(np.pi * a * 4)), np.abs(np.sin(np.pi * b * 4)))
    shade = groove + (1 - groove) * hgt * (0.8 + 0.2 * fine)
    rgb = srgb(base_hex)[None, None] * shade[..., None]
    gy, gx = np.gradient(hgt)
    nrm = np.stack([-gx * 6, -gy * 6, np.ones_like(hgt)], 2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return (image(probe, f"{name}_base", np.clip(rgb, 0, 1).astype(np.float32), "sRGB"),
            image(probe, f"{name}_normal", (nrm * 0.5 + 0.5).astype(np.float32), "Non-Color"))

def _cells(U, V, repeat, size_u, size_v, rng):
    """Jittered-grid Voronoi that wraps at the edges: one random point in each grid cell
    (about `size_u` x `size_v` metres), and for every pixel the index of its nearest point plus
    the distances to the nearest and second-nearest, with u distances divided by size_u / size_v
    (so stretched cells stay stretched). Only the 3 x 3 neighbouring cells are searched."""
    nu = max(3, int(round(repeat[0] / size_u)))
    nv = max(3, int(round(repeat[1] / size_v)))
    cu, cv = repeat[0] / nu, repeat[1] / nv
    jit = rng.uniform(0, 1, (nv, nu, 2))
    iu = np.floor(U / cu).astype(int) % nu
    iv = np.floor(V / cv).astype(int) % nv
    d1 = np.full(U.shape, np.inf)
    d2 = np.full(U.shape, np.inf)
    idx = np.zeros(U.shape, int)
    aspect = cu / cv
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ju, jv = (iu + di) % nu, (iv + dj) % nv
            pu = (np.floor(U / cu) + di + jit[jv, ju, 0]) * cu
            pv = (np.floor(V / cv) + dj + jit[jv, ju, 1]) * cv
            d = np.hypot((U - pu) / aspect, V - pv)
            near = d < d1
            d2 = np.where(near, d1, np.minimum(d2, d))
            d1 = np.where(near, d, d1)
            idx = np.where(near, jv * nu + ju, idx)
    return idx, d1, d2, nu * nv

def crinkled_foil(probe, name, base_hex, repeat=(0.6, 0.6), facet=0.04, tilt_deg=14.0,
                  wrinkle=0.12, wrinkle_deg=10.0, spread=0.10, stretch=1.0, pillow=None,
                  pillow_deg=20.0, px_per_m=900, seed=7):
    """Colour and normal map of crinkled foil (a thermal blanket's outer layer): flat facets
    about `facet` metres across, each tilted at random by up to `tilt_deg` (the creases between
    them catch the light), over broad wrinkles about `wrinkle` metres across that lean the skin
    by up to `wrinkle_deg`. Each facet's brightness varies by up to `spread`. `stretch` > 1
    draws the facets that many times longer along u than v (folds running one way). `pillow`:
    the blanket puffs up in cells about that many metres across, each puffed by a different
    amount, pinched down at their edges (where it is tied to the skin), sloping by up to
    `pillow_deg`. Repeats seamlessly over `repeat` metres (u, v): map it with cyl_uv / plane_uv.
    To avoid a visible repeat on a body of revolution, make one image per section: u = its
    circumference, v = its length. Returns (base, normal)."""
    w = int(round(repeat[0] * px_per_m))
    h = int(round(repeat[1] * px_per_m))
    rng = np.random.default_rng(seed)
    U, V = np.meshgrid((np.arange(w) + 0.5) / w * repeat[0], (np.arange(h) + 0.5) / h * repeat[1])
    cell, _, _, n_pts = _cells(U, V, repeat, facet * stretch, facet, rng)
    t = np.tan(np.radians(tilt_deg)) * np.sqrt(rng.uniform(0, 1, n_pts))
    a = rng.uniform(0, 2 * np.pi, n_pts)
    sx, sy = (t * np.cos(a))[cell], (t * np.sin(a))[cell]
    hgt = _noise(h, w, wrinkle * px_per_m, wrinkle * px_per_m, seed + 1)
    gy, gx = np.gradient(hgt)
    k = np.tan(np.radians(wrinkle_deg)) / (np.abs(np.stack([gx, gy])).max() + 1e-9)
    sx, sy = sx + gx * k, sy + gy * k
    if pillow:
        pc, d1, d2, n_cells = _cells(U, V, repeat, pillow, pillow, rng)
        edge = (d2 - d1) / pillow                # 0 on a cell's edge, rising inwards
        amp = rng.uniform(0.4, 1.0, n_cells)[pc]  # some cells puff more than others
        puff = np.sqrt(np.clip(edge * 2.0, 0, 1)) * amp
        puff = _blur_wrap(puff, px_per_m * pillow * 0.08)
        py, px_ = np.gradient(puff)
        kp = np.tan(np.radians(pillow_deg)) / (np.abs(np.stack([px_, py])).max() + 1e-9)
        sx, sy = sx + px_ * kp, sy + py * kp
    nrm = np.stack([-sx, -sy, np.ones_like(hgt)], 2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    shade = 1 + spread * rng.uniform(-1, 1, n_pts)[cell]
    rgb = srgb(base_hex)[None, None] * shade[..., None]
    return (image(probe, f"{name}_base", np.clip(rgb, 0, 1).astype(np.float32), "sRGB"),
            image(probe, f"{name}_normal", (nrm * 0.5 + 0.5).astype(np.float32), "Non-Color"))

def panel_grid(probe, name, base_hex, cell=(0.75, 0.5), seam=0.012, darken=0.55, rivet=0.006,
               rivet_pitch=0.04, spread=0.04, cells=(4, 4), px_per_m=400, seed=5):
    """Colour and normal map of a skin laid in rectangular panels or tape (Hubble's aft shroud):
    seams `seam` wide every `cell` (u, v) metres, darkened to `darken`, rivet dots `rivet` across
    every `rivet_pitch` along each seam's sides, and each panel's brightness varied by up to
    `spread`. The image holds `cells` panels across and up, so it repeats every cell x cells.
    Returns (base, normal)."""
    rep = (cell[0] * cells[0], cell[1] * cells[1])
    w, h = int(round(rep[0] * px_per_m)), int(round(rep[1] * px_per_m))
    U, V = np.meshgrid((np.arange(w) + 0.5) / px_per_m, (np.arange(h) + 0.5) / px_per_m)
    du = np.abs((U + cell[0] / 2) % cell[0] - cell[0] / 2)     # distance to the nearest seam
    dv = np.abs((V + cell[1] / 2) % cell[1] - cell[1] / 2)
    line = np.clip(1 - (np.minimum(du, dv) - seam / 2) * px_per_m, 0, 1)
    # rivets: a row each side of every seam
    off = seam / 2 + rivet * 1.2
    ru = np.hypot(np.abs(du - off), ((V % rivet_pitch) - rivet_pitch / 2))
    rv = np.hypot(np.abs(dv - off), ((U % rivet_pitch) - rivet_pitch / 2))
    dots = np.clip(1 - (np.minimum(ru, rv) - rivet / 2) * px_per_m, 0, 1)
    rng = np.random.default_rng(seed)
    shade_cells = 1 + spread * rng.uniform(-1, 1, (cells[1], cells[0]))
    iu = np.minimum((U // cell[0]).astype(int), cells[0] - 1)
    iv = np.minimum((V // cell[1]).astype(int), cells[1] - 1)
    shade = shade_cells[iv, iu] * (1 - line * (1 - darken)) * (1 - dots * 0.25)
    rgb = srgb(base_hex)[None, None] * shade[..., None]
    hgt = -line * 0.6 + dots * 0.8
    gy, gx = np.gradient(_blur_wrap(hgt, 1.0))
    nrm = np.stack([-gx * 3, -gy * 3, np.ones_like(hgt)], 2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return (image(probe, f"{name}_base", np.clip(rgb, 0, 1).astype(np.float32), "sRGB"),
            image(probe, f"{name}_normal", (nrm * 0.5 + 0.5).astype(np.float32), "Non-Color"))
