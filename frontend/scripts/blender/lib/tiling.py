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
