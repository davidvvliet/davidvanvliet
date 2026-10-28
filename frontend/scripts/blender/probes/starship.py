# Starship V3, full stack. Built from lib/parts in metres; every number comes from
# specs/starship.json ("dimensions", "facts", "from_photos", each with its source).
# Frame: z up, engine bell exits at z = 0, axis on x = y = 0; +x is the ship's windward
# (heat-shield) side, away from the tower.
import math, os
import bpy
import numpy as np
from lib import materials, parts

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HARNESS, "out", "starship", "textures")

def _at(angle_deg, r, z):
    a = math.radians(angle_deg)
    return (r * math.cos(a), r * math.sin(a), z)

def _srgb(hexstr):
    h = hexstr.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

def _image(name, rgb, colorspace):
    """Save rgb (rows bottom-up, values as stored) as a JPEG the export keeps as JPEG, marked
    as a repeating pattern for checks.textures."""
    os.makedirs(OUT, exist_ok=True)
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.concatenate([rgb, np.ones((h, w, 1), np.float32)], 2).ravel())
    img.filepath_raw = os.path.join(OUT, f"{name}.jpg")
    img.file_format = "JPEG"
    bpy.context.scene.render.image_settings.quality = 90
    img.save()
    img["tiling"] = True
    return img

def _hex_tiles(t, tile_hex, repeat_w, px_per_m=480):
    """Colour and normal map of hexagonal tiles in staggered horizontal rows (vertices up),
    `repeat_w` wide (4 tiles) and two row pairs tall, so it repeats seamlessly."""
    d = repeat_w / 4                                   # across flats = centre spacing in a row
    H = 2 * d * math.sqrt(3)
    w, h = int(round(repeat_w * px_per_m)), int(round(H * px_per_m))
    x = (np.arange(w) + 0.5) / w * repeat_w
    y = (np.arange(h) + 0.5) / h * H
    X, Y = np.meshgrid(x, y)
    cs, ids = [], []
    for k in range(-2, 7):
        for m in range(-2, 7):
            cs.append((m * d + (k % 2) * d / 2, k * d * math.sqrt(3) / 2))
            ids.append((m % 4) * 4 + (k % 4))
    cs, ids = np.array(cs), np.array(ids)
    D2 = (X[..., None] - cs[:, 0]) ** 2 + (Y[..., None] - cs[:, 1]) ** 2
    order = np.argsort(D2, axis=2)[..., :2]
    d1 = np.take_along_axis(D2, order[..., :1], 2)[..., 0]
    d2 = np.take_along_axis(D2, order[..., 1:2], 2)[..., 0]
    edge = (d2 - d1) / (2 * d)                         # distance to the cell's edge (m)
    inside = np.clip((edge - t["gap"] / 2) / 0.004, 0, 1)
    rng = np.random.default_rng(39)
    shade = 1 + t["shade_spread"] * rng.uniform(-1, 1, 16)
    tile = _srgb(tile_hex)[None, None] * shade[ids[order[..., 0]]][..., None]
    gap = _srgb(tile_hex) * t["gap_brightness"]
    rgb = tile * inside[..., None] + gap[None, None] * (1 - inside[..., None])
    hgt = -(1 - inside) * t["gap"] / 2                # gaps sit below the tile faces
    step = repeat_w / w
    dy, dx = np.gradient(hgt, step)
    n = np.stack([-dx, -dy, np.ones_like(hgt)], 2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return (_image("heat_shield_tiles_base", np.clip(rgb, 0, 1).astype(np.float32), "sRGB"),
            _image("heat_shield_tiles_normal", (n * 0.5 + 0.5).astype(np.float32), "Non-Color"),
            H)

def _weld_lines(steel_hex, ring_h, line, darken, px_per_m=280):
    """Steel with a darker weld line every `ring_h` metres (u doesn't matter: 8 px wide)."""
    h = int(round(ring_h * px_per_m))
    v = (np.arange(h) + 0.5) / h * ring_h
    dist = np.minimum(v, ring_h - v)
    k = np.clip(dist / (line / 2), 0, 1)
    shade = darken + (1 - darken) * k
    rgb = _srgb(steel_hex)[None, None] * shade[:, None, None] * np.ones((1, 8, 1))
    return _image("stainless_steel_welds", rgb.astype(np.float32), "sRGB")

def _cyl_uv(obj, repeat_w, repeat_h, R):
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

def _plane_uv(obj, across, repeat_w, repeat_h):
    """UVs for a flat part: u along the world direction `across`, v = z."""
    me, mw = obj.data, obj.matrix_world
    uv = me.uv_layers.new(name="UVMap")
    for li, loop in enumerate(me.loops):
        p = mw @ me.vertices[loop.vertex_index].co
        uv.data[li].uv = ((p.x * across[0] + p.y * across[1]) / repeat_w, p.z / repeat_h)

def build(spec):
    D = {k: v["value"] for k, v in spec["dimensions"].items()}
    F = {k: v["value"] for k, v in spec["facts"].items()}
    P = {k: v["value"] for k, v in spec["from_photos"].items()}
    R = D["diameter_booster"] / 2
    top = D["stack_height"]
    hb = D["booster_height"]
    hs = D["ship_height"]
    steel, tiles = "stainless_steel", "heat_shield_tiles"
    # Surface detail: hexagonal tiles and weld lines as repeating textures
    # (from_photos.hex_tiles, facts.ring_height). A whole number of tile repeats goes round.
    ht = P["hex_tiles"]
    reps = round(2 * math.pi * R / (4 * ht["across_flats"]))
    tile_w = 2 * math.pi * R / reps
    sm = spec["materials"]
    tbase, tnorm, tile_h = _hex_tiles(ht, sm[tiles]["hex"], tile_w)
    tiles_tex = materials.image("heat_shield_tiles_textured", tbase, tnorm,
                                metallic=sm[tiles]["metallic"], roughness=sm[tiles]["roughness"])
    welds = _weld_lines(sm[steel]["hex"], F["ring_height"], ht["weld_line"], ht["weld_darken"])
    steel_tex = materials.image("stainless_steel_textured", welds, metallic=sm[steel]["metallic"],
                                roughness=sm[steel]["roughness"])

    # --- Super Heavy -------------------------------------------------------------------
    with parts.assembly("booster", core=True):
        aft = P["booster_engines_below_skirt"]
        ring_h = P["hot_stage_ring_height"]
        tank_top = hb - ring_h
        tank = parts.cylinder("booster_tank", R, tank_top - aft, location=(0, 0, aft), segments=64,
                              material=steel_tex)
        _cyl_uv(tank, 1.0, F["ring_height"], R)

        # 33 bells: 3 centre, 10 middle, 20 outer (facts.booster_engine_rings). Bell profile:
        # exit at z = 0, throat 1.53 m up (faa_plume's throat-to-exit length), powerhead into
        # the aft plate.
        ex = P["booster_nozzle_exit"] / 2
        bell = [(0, 0.15), (ex, 0), (ex * 0.85, 0.5), (ex * 0.6, 1.1), (0.25, 1.53),
                (0.4, 1.8), (0.4, aft + 0.2), (0, aft + 0.2)]
        c = F["booster_centre_engine_clocking_deg"]
        centre = [90, 90 + c[0], 90 + c[0] + c[1]]
        rings = [(0.85, centre), (2.4, [18 + 36 * k for k in range(10)]),
                 (3.9, [9 + 18 * k for k in range(20)])]
        k = 0
        for r, angles in rings:
            for a in angles:
                parts.lathe(f"booster_engine_{k:02d}", bell, location=_at(a, r, 0), segments=16,
                            material="dark_metal")
                k += 1

        # Chines: strakes on +y and -y over the lower booster, tapering in at the top.
        ch = P["booster_chines"]
        for sign, tag in parts.sides():
            y0, y1 = sign * (R - 0.05), sign * (R + ch["stands_out"])
            z_top = aft + ch["top_above_aft_end"]
            parts.surface(f"booster_chine_{tag}", root_le=(0, y0, z_top), root_chord=z_top - aft,
                          tip_le=(0, y1, z_top - 3.0), tip_chord=z_top - 3.0 - aft,
                          thickness=0.03, chord_dir=(0, 0, -1), material=steel)

        rw = P["booster_raceway"]
        parts.box("booster_raceway", (rw["stands_out"] + 0.1, rw["width"], tank_top - aft - 0.4),
                  location=_at(rw["angle_from_x_deg"], R + rw["stands_out"] / 2 - 0.05,
                               (aft + tank_top) / 2),
                  roll_deg=rw["angle_from_x_deg"], material=steel)

        # Integrated hot stage: the methane tank's exposed dome inside a crown of V struts
        # that carries a ring the ship stands on.
        hsr = P["hot_stage_struts"]
        dh = hsr["dome_height"]
        dome = [(R, 0)] + [(R * math.cos(t), dh * math.sin(t))
                           for t in [math.radians(x) for x in range(15, 90, 15)]] + [(0, dh)]
        parts.lathe("booster_dome", dome, location=(0, 0, tank_top - 0.01), segments=48,
                    material=steel)
        ring_t = 0.3
        parts.lathe("hotstage_ring", [(R - 0.25, hb - ring_t), (R, hb - ring_t), (R, hb),
                                      (R - 0.25, hb)], closed=True, segments=64, smooth=False,
                    material=steel)
        n = hsr["v_pairs"]
        sr = hsr["strut_diameter"] / 2
        for i in range(n):
            foot = _at(360 * i / n, R - sr, tank_top - 0.3)
            for j, da in enumerate((-180 / n, 180 / n)):
                head = _at(360 * i / n + da, R - sr, hb - ring_t / 2)
                parts.strut(f"hotstage_strut_{i:02d}_{j}", foot, head, radius=sr, segments=8,
                            material=steel)

        # A ribbed band of fittings round the booster (from_photos.booster_band).
        bd = P["booster_band"]
        b1 = hb - bd["top_below_booster_top"]
        b0 = b1 - bd["height"]
        parts.lathe("booster_band", [(R - 0.05, b0), (R + bd["stands_out"], b0),
                                     (R + bd["stands_out"], b1), (R - 0.05, b1)], closed=True,
                    segments=64, smooth=False, material="dark_metal")

        # Grid fins: three, in a T (90/90/180): +y, -y and the heat-shield side (+x).
        gf = P["grid_fin"]
        zc = hb - gf["top_below_booster_top"] - gf["thickness"] / 2
        for a, tag in ((90, "left"), (-90, "right"), (0, "windward")):
            parts.grid_fin(f"grid_fin_{tag}", gf["stands_out"] + 0.1, gf["width"], gf["thickness"],
                           gf["pitch"], location=_at(a, R - 0.1, zc), direction=_at(a, 1, 0),
                           wall=gf["wall"], notch=gf["notch"], notch_top=0.0,
                           material="grid_fin")

    # --- Starship ----------------------------------------------------------------------
    with parts.assembly("ship"):
        z0 = top - hs                       # ship base, on the hot-stage ring
        L = P["nose_length"]
        z_nose = top - L
        rn = P["nose_tip_radius"]

        # Blunted tangent ogive: a sphere of radius rn on the tip, tangent to the ogive. The
        # sharp ogive's length Ls is solved so the blunted nose is L long (nose to full width).
        def blunted(Ls):
            rho = (R * R + Ls * Ls) / (2 * R)
            x0 = Ls - math.sqrt((rho - rn) ** 2 - (rho - R) ** 2)   # sphere centre, from the sharp tip
            yt = rn * (rho - R) / (rho - rn)
            xt = x0 - math.sqrt(rn * rn - yt * yt)                  # where sphere meets ogive
            return rho, x0, xt, x0 - rn                             # last: blunted apex
        Ls = L
        for _ in range(30):
            Ls += L - (Ls - blunted(Ls)[3])
        rho, x0, xt, xa = blunted(Ls)

        def r_at(z):
            x = (top - z) + xa              # distance from the sharp ogive's tip
            if x >= Ls:
                return R
            if x <= xa:
                return 0.0
            if x < xt:
                return math.sqrt(max(0.0, rn * rn - (x - x0) ** 2))
            return math.sqrt(rho * rho - (Ls - x) ** 2) + R - rho

        tl = P["tile_layout"]
        z_cap, z_wrap = top - tl["tip_cap_below_tip"], top - tl["flap_wrap_below_tip"]
        zt_join = top - (xt - xa)
        zs = [z_nose + (zt_join - z_nose) * i / 14 for i in range(1, 15)]
        zs += [zt_join + (top - zt_join) * i / 6 for i in range(1, 6)]
        zs = sorted(set(zs) | {z_cap})
        prof = [(0, z0), (R, z0), (R, z_wrap), (R, z_nose)] + [(r_at(z), z) for z in zs]
        prof += [(0, top)]
        # One skin, tiles or steel per face (facts.heat_shield, from_photos.tile_layout):
        # black on the windward half, all round the top of the nose, and round the forward
        # flaps' roots; bare steel elsewhere. 64 segments put edges at 90 and 118.1 degrees.
        body = parts.lathe("ship_body", prof, segments=64, material=[tiles_tex, steel_tex])
        for poly in body.data.polygons:
            c = poly.center
            ang = abs(math.degrees(math.atan2(c.y, c.x)))
            tiled = (c.z > z_cap or ang <= tl["barrel_to_deg"] + 0.1
                     or (c.z > z_wrap and ang <= tl["flap_wrap_deg"] + 0.2))
            poly.material_index = 0 if tiled else 1
        # One UV map serves both: tile repeats for the tiles, weld lines (1.83 m) for the
        # steel. The weld image is one ring tall, the tile image two row pairs, so v is scaled
        # per material below.
        _cyl_uv(body, tile_w, tile_h, R)
        uv = body.data.uv_layers.active.data
        for poly in body.data.polygons:
            if poly.material_index == 1:
                for li in poly.loop_indices:
                    u, v = uv[li].uv
                    uv[li].uv = (u * tile_w, v * tile_h / F["ring_height"])

        # Forward flaps: leeward, 140 degrees apart; root along the nose, bottom edge level.
        ff = P["forward_flap"]
        zb = top - ff["bottom_below_tip"]
        zt = zb + ff["root_chord"]
        for a, tag in ((180 - 70, "left"), (180 + 70, "right")):
            ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
            rt, rb = r_at(zt) - 0.05, r_at(zb) - 0.05
            top_pt, bot_pt = (ux * rt, uy * rt, zt), (ux * rb, uy * rb, zb)
            chord = math.dist(top_pt, bot_pt)
            cd = tuple((b - t) / chord for t, b in zip(top_pt, bot_pt))
            rtip = rb + 0.05 + ff["span"]
            tip_bot = (ux * rtip, uy * rtip, zb)
            tip_le = tuple(b - d * ff["tip_chord"] for b, d in zip(tip_bot, cd))
            flap = parts.surface(f"ship_forward_flap_{tag}", root_le=top_pt, root_chord=chord,
                                 tip_le=tip_le, tip_chord=ff["tip_chord"], thickness=0.05,
                                 chord_dir=cd, material=tiles_tex)
            _plane_uv(flap, (ux, uy), tile_w, tile_h)

        # Aft flaps: +y and -y, root down to the ship's base.
        af = P["aft_flap"]
        for sign, tag in parts.sides():
            flap = parts.surface(f"ship_aft_flap_{tag}",
                                 root_le=(0, sign * (R - 0.05), z0 + af["root_chord"]),
                                 root_chord=af["root_chord"],
                                 tip_le=(0, sign * (R + af["span"]), z0 + af["tip_chord"]),
                                 tip_chord=af["tip_chord"], thickness=0.04, chord_dir=(0, 0, -1),
                                 material=tiles_tex)
            _plane_uv(flap, (0, sign), tile_w, tile_h)
            # Actuator housing on the body at the top of the flap's root.
            hz = P["aft_flap_housing"]
            parts.box(f"ship_aft_flap_housing_{tag}", (hz["width"], hz["stands_out"] + 0.1, hz["height"]),
                      location=(0, sign * (R + hz["stands_out"] / 2 - 0.05),
                                z0 + af["root_chord"] - hz["height"] / 2),
                      material=tiles)
