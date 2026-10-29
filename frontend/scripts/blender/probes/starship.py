# Starship V3, the ship (upper stage). Built from lib/parts in metres; every number comes from
# specs/starship.json ("dimensions", "facts", "from_photos", each with its source).
# Frame: z up, the ship's base (aft skirt) at z = 0, axis on x = y = 0; +x is the windward
# (heat-shield) side, away from the tower. The booster is its own model (superheavy).
import math, os
import bmesh
import numpy as np
from mathutils import Vector
from lib import engines, materials, parts, textures, tiling

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HARNESS, "out", "starship", "textures")

def _at(angle_deg, r, z):
    a = math.radians(angle_deg)
    return (r * math.cos(a), r * math.sin(a), z)

def _bell(exit_r, throat_r, throat_z, top, wall=0.03):
    """Engine bell profile, exit at z = 0: hollow, flared to `exit_r` from a throat `throat_r`
    at `throat_z`, with a powerhead up to `top`. Down the inside from the throat, round the
    lip, up the outside."""
    curve = [(exit_r, 0), (exit_r * 0.86, throat_z * 0.33), (exit_r * 0.62, throat_z * 0.7),
             (throat_r, throat_z)]
    inside = [(r - wall, z + wall * 0.5) for r, z in reversed(curve)]
    return ([(0, throat_z)] + inside + curve
            + [(throat_r * 1.6, throat_z + 0.3), (throat_r * 1.6, top), (0, top)])

def _sheet(name, r, a0, a1, z0, z1, material, segments=48):
    """A curved sheet on the leeward side: radius `r`, from angle `a0` to `a1` (degrees),
    `z0` to `z1`, facing out, UVs in metres (u along the arc from a0, v = z - z0)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    angs = [math.radians(a0 + (a1 - a0) * i / segments) for i in range(segments + 1)]
    lo = [bm.verts.new((r * math.cos(a), r * math.sin(a), z0)) for a in angs]
    hi = [bm.verts.new((r * math.cos(a), r * math.sin(a), z1)) for a in angs]
    for i in range(segments):
        f = bm.faces.new((lo[i], lo[i + 1], hi[i + 1], hi[i]))
        f.normal_update()
        c = f.calc_center_median()
        if f.normal.dot(Vector((c.x, c.y, 0))) < 0:
            f.normal_flip()
        for loop in f.loops:
            a = math.atan2(loop.vert.co.y, loop.vert.co.x) % (2 * math.pi)
            loop[uv].uv = ((a - math.radians(a0)) * r, loop.vert.co.z - z0)
    obj = parts._object(name, bm, material, parts.frame(), smooth=True)
    obj.data.normals_split_custom_set_from_vertices(
        [Vector((v.co.x, v.co.y, 0)).normalized() for v in obj.data.vertices])
    return obj

def _rgb(entry):
    h = entry["hex"].lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

def build(spec):
    D = {k: v["value"] for k, v in spec["dimensions"].items()}
    F = {k: v["value"] for k, v in spec["facts"].items()}
    P = {k: v["value"] for k, v in spec["from_photos"].items()}
    R = D["diameter"] / 2
    top = D["height"]
    steel, tiles = "stainless_steel", "heat_shield_tiles"
    # Surface detail: hexagonal tiles and weld lines as repeating textures
    # (from_photos.hex_tiles, from_photos.weld_lines, facts.ring_height). A whole number of
    # tile repeats goes round; each repeat is cols x rows tiles, every one shaded on its own.
    ht = P["hex_tiles"]
    cols, rows = ht["repeat_tiles"]
    reps = round(2 * math.pi * R / (cols * ht["across_flats"]))
    tile_w = 2 * math.pi * R / reps
    d = tile_w / cols                       # across flats, as fitted
    sm = spec["materials"]
    tbase, tnorm, tile_h = tiling.hex_tiles("starship", ht, sm[tiles]["hex"], tile_w, cols, rows)
    tiles_tex = materials.image("heat_shield_tiles_textured", tbase, tnorm,
                                metallic=sm[tiles]["metallic"], roughness=sm[tiles]["roughness"])
    wl = P["weld_lines"]
    welds = tiling.weld_lines("starship", sm[steel]["hex"], F["ring_height"], wl["line"], wl["darken"])
    steel_tex = materials.image("stainless_steel_textured", welds, metallic=sm[steel]["metallic"],
                                roughness=sm[steel]["roughness"])

    def steel_uv(obj):
        # One UV map serves both: tile repeats for the tiles, weld lines (1.83 m) for the steel.
        # The weld image is one ring tall, the tile image `rows` rows, so v is scaled per material.
        tiling.cyl_uv(obj, tile_w, tile_h, R)
        uv = obj.data.uv_layers.active.data
        for poly in obj.data.polygons:
            if poly.material_index == 1:
                for li in poly.loop_indices:
                    u, v = uv[li].uv
                    uv[li].uv = (u * tile_w, v * tile_h / F["ring_height"])

    with parts.assembly("ship", core=True):
        z0 = 0.0                            # ship base
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
        # The skirt is open: an engine bay `bay_depth` deep inside a thin wall
        # (from_photos.engines).
        en = P["engines"]
        bay, wall = en["bay_depth"], en["skirt_wall"]
        # The bay's ceiling is the aft dome: the sea-level engines hang from its flat centre,
        # the vacuum engines from its slope (from_photos.engines.aft_dome).
        prof = [tuple(q) for q in en["aft_dome"]] + [(R - wall, z0), (R, z0), (R, z_wrap), (R, z_nose)]
        prof += [(r_at(z), z) for z in zs] + [(0, top)]
        # One skin, tiles or steel per face (facts.heat_shield, from_photos.tile_layout):
        # black on the windward half, all round the top of the nose, and round the forward
        # flaps' roots; bare steel elsewhere; the engine bay dark. 64 segments put edges at
        # 90 and 118.1 degrees.
        body = parts.lathe("ship_body", prof, segments=64,
                           material=[tiles_tex, steel_tex, "dark_metal"])
        for poly in body.data.polygons:
            c = poly.center
            ang = abs(math.degrees(math.atan2(c.y, c.x)))
            if c.z < bay + 1e-3 and math.hypot(c.x, c.y) < R - wall / 2:  # bay, dome included
                poly.material_index = 2
                continue
            tiled = (c.z > z_cap or ang <= tl["barrel_to_deg"] + 0.1
                     or (c.z > z_wrap and ang <= tl["flap_wrap_deg"] + 0.2))
            poly.material_index = 0 if tiled else 1

        # Jagged tile edge along the barrel (from_photos.tile_edge): the tiles stop on whole
        # hexagons, so the edge follows the tiles' sides and steps half a tile every row. The
        # two face columns either side of +-90 degrees are cut out of the body below the flap
        # wrap and rebuilt as a strip whose middle edge runs along the hexagons. Tile centres
        # are where hex_tiles puts them: (m d + (k % 2) d / 2, k row) in (angle x R, z).
        seg = 2 * math.pi / 64
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bm.faces.ensure_lookup_table()
        cut = [f for f in bm.faces
               if f.calc_center_median().z < z_wrap and f.calc_center_median().z > z0 + 1e-3
               and abs(abs(math.atan2(f.calc_center_median().y, f.calc_center_median().x)) - math.pi / 2) < seg
               and f.calc_center_median().xy.length > R - wall / 2]
        bmesh.ops.delete(bm, geom=cut, context="FACES_ONLY")
        bm.to_mesh(body.data)
        bm.free()
        steel_uv(body)

        row = d * math.sqrt(3) / 2
        side_len = d / math.sqrt(3)
        ub = R * math.radians(tl["barrel_to_deg"])
        for sign, tag in ((1, "left"), (-1, "right")):
            pts = []
            for k in range(-1, int(z_wrap / row) + 2):
                off = (k % 2) * d / 2
                if sign > 0:   # last tile in the row: centre below +ub; edge on its right side
                    m = math.ceil((ub - off) / d) - 1
                    x = m * d + off + d / 2
                else:          # first tile above -ub; edge on its left side
                    m = math.floor((-ub - off) / d) + 1
                    x = m * d + off - d / 2
                pts += [(x, k * row - side_len / 2), (x, k * row + side_len / 2)]
            # Clip to the strip's height.
            clipped = []
            for (xa_, za), (xb, zb) in zip(pts, pts[1:]):
                for zc in (z0, z_wrap):
                    if (za - zc) * (zb - zc) < 0:
                        clipped.append((xa_ + (xb - xa_) * (zc - za) / (zb - za), zc))
                if z0 <= zb <= z_wrap:
                    clipped.append((xb, zb))
            clipped.sort(key=lambda p: p[1])
            lo, hi = sorted((sign * (math.pi / 2 - seg), sign * (math.pi / 2 + seg)))
            bm = bmesh.new()
            cyl = lambda u, z: bm.verts.new((R * math.cos(u / R), R * math.sin(u / R), z))
            ring = [(cyl(lo * R, z), cyl(x, z), cyl(hi * R, z)) for x, z in clipped]
            for a, b in zip(ring, ring[1:]):
                for j in (0, 1):
                    f = bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
                    f.normal_update()
                    c = f.calc_center_median()
                    if f.normal.dot(Vector((c.x, c.y, 0))) < 0:
                        f.normal_flip()
                    # Tiles on the windward side of the edge (the low-u half for +y).
                    f.material_index = 0 if (j == 0) == (sign > 0) else 1
            strip = parts._object(f"ship_tile_edge_{tag}", bm, [tiles_tex, steel_tex],
                                  parts.frame(), smooth=True)
            strip.data.normals_split_custom_set_from_vertices(
                [Vector((v.co.x, v.co.y, 0)).normalized() for v in strip.data.vertices])
            steel_uv(strip)

        # Engines: 3 sea-level Raptors in the middle, 3 Raptor Vacuums round them, inside the
        # skirt (facts.ship_engines, from_photos.engines).
        # The engines are models of their own (specs/raptor3.json, specs/raptor3vac.json): the
        # engines in the bay at the simple level of detail (seen from below, low shows facets).
        r3, r3v = engines.load(spec, "raptor3"), engines.load(spec, "raptor3vac")
        for i, a in enumerate(en["sl_angles_deg"]):
            engines.place(r3, f"ship_engine_sl_{i}", location=_at(a, en["sl_ring_radius"], en["sl_exit_above_base"]),
                          roll_deg=a + en["sl_roll_deg"], lod="simple")
        for i, a in enumerate(en["rvac_angles_deg"]):
            engines.place(r3v, f"ship_engine_vac_{i}", location=_at(a, en["rvac_ring_radius"], en["rvac_exit_above_base"]),
                          roll_deg=a + en["rvac_roll_deg"], lod="simple")
            # Heavy brackets on the skirt wall either side of each vacuum bell.
            b = en["rvac_brackets"]
            for side in (-1, 1):
                ab = a + side * b["offset_deg"]
                parts.box(f"ship_bay_bracket_{i}_{'ab'[side > 0]}", b["size"],
                          location=_at(ab, R - wall - b["size"][0] / 2, b["z"]), roll_deg=ab,
                          material="dark_metal")
        # The aft dome's underside: bolted panels (from_photos.aft_dome_panels), a texture on a
        # sheet just below the body's dome, mapped flat from below.
        dp = P["aft_dome_panels"]
        n = dp["texture_px"]
        yy, xx = np.mgrid[0:n, 0:n]
        X, Y = (xx + 0.5) / n * 2 * R - R, (yy + 0.5) / n * 2 * R - R
        rr, aa = np.hypot(X, Y), np.degrees(np.arctan2(Y, X)) % 360
        px_m = n / (2 * R)
        plate, seam = _rgb(sm["aft_dome_plate"]), _rgb(sm["aft_dome_plate"]) * 0.55
        img = np.repeat(np.repeat(plate[None, None], n, 0), n, 1)
        da = (aa + dp["radial_every_deg"] / 2) % dp["radial_every_deg"] - dp["radial_every_deg"] / 2
        on_radial = (np.abs(np.radians(da)) * rr * px_m < 1.0) & (rr > dp["rings_r"][0])
        on_ring = np.zeros_like(on_radial)
        for rk in dp["rings_r"]:
            on_ring |= np.abs(rr - rk) * px_m < 1.0
        img[on_radial | on_ring] = seam
        # Bolt heads: dots beside each seam, `bolt_spacing` apart along it.
        bs = dp["bolt_spacing"]
        near_r = (np.abs(np.abs(np.radians(da)) * rr - 0.035) * px_m < 1.2) & (rr > dp["rings_r"][0])
        along = (rr % bs) * px_m < 2.4
        near_c = np.zeros_like(near_r)
        for rk in dp["rings_r"]:
            near_c |= np.abs(np.abs(rr - rk) - 0.035) * px_m < 1.2
        along_c = ((np.radians(aa) * rr) % bs) * px_m < 2.4
        img[(near_r & along) | (near_c & along_c)] = seam * 0.8
        dome_img = tiling.image("starship", "aft_dome_panels", img.astype(np.float32), "sRGB")
        dome_mat = materials.image("aft_dome_panels", dome_img, metallic=sm["aft_dome_plate"]["metallic"],
                                   roughness=sm["aft_dome_plate"]["roughness"])
        dome = parts.lathe("ship_aft_dome", [(r, z - 0.006) for r, z in en["aft_dome"]], segments=64,
                           material=dome_mat)
        uvl = dome.data.uv_layers.new(name="UVMap")
        for loop in dome.data.loops:
            co = dome.data.vertices[loop.vertex_index].co
            uvl.data[loop.index].uv = (co.x / (2 * R) + 0.5, co.y / (2 * R) + 0.5)

        def dome_z(r):
            pts = en["aft_dome"]
            for (r0, z0_), (r1, z1_) in zip(pts, pts[1:]):
                if r0 <= r <= r1:
                    return z0_ + (z1_ - z0_) * (r - r0) / (r1 - r0)
            return pts[-1][1]

        # Cables across the dome (from_photos.bay_cables).
        bc = P["bay_cables"]
        for k, run in enumerate(bc["runs"]):
            parts.tube(f"ship_bay_cable_{k}", [_at(a, r, dome_z(r) - bc["hang"]) for r, a in run],
                       bc["diameter"] / 2, segments=6, bend_radius=0.4, bend_steps=3, material="bay_cable")

        # Aft flap actuators (from_photos.flap_actuators): one housing per flap on the skirt's
        # inside wall, three motors standing out of it.
        fa = P["flap_actuators"]
        for tag, a in (("left", 90), ("right", 270)):
            hr, hw, hh = fa["housing"]
            parts.box(f"ship_flap_actuator_{tag}", (hr, hw, hh), location=_at(a, R - wall - hr / 2, fa["z"]),
                      roll_deg=a, material="dark_metal")
            for m in range(fa["motors"]):
                off = (m - (fa["motors"] - 1) / 2) * hw / fa["motors"]
                c = Vector(_at(a, R - wall - hr - fa["motor_length"] / 2 + 0.02, fa["z"] + hh * 0.15))
                c += Vector(_at(a + 90, 1, 0)) * off
                parts.cylinder(f"ship_flap_actuator_{tag}_motor_{m}", fa["motor_diameter"] / 2,
                               fa["motor_length"], location=tuple(c), direction=_at(a + 180, 1, 0),
                               segments=12, material="aft_hardware_dark")

        # Stiffening rings round the inside of the skirt.
        sr = en["skirt_rings"]
        for k in range(sr["count"]):
            z = sr["from"] + (sr["to"] - sr["from"]) * k / (sr["count"] - 1)
            ri = R - wall - sr["stands_in"]
            # Only the faces seen from the bay: the underside and the inner edge.
            parts.lathe(f"ship_skirt_ring_{k:02d}", [(R - wall + 0.005, z), (ri, z), (ri, z + sr["height"])],
                        segments=48, smooth=False, material="dark_metal")

        # Flap hinges (from_photos.flap_hinges): each flap stands off the body on brackets,
        # turning on a rod between them.
        fh = P["flap_hinges"]
        def hinge(name, root_top, root_bot, out_dir, standoff, fractions, r_body):
            """Rod along the root, `standoff` out from the body, and brackets at `fractions`."""
            ux, uy = out_dir
            rod = lambda p, f: (p[0] + ux * f, p[1] + uy * f, p[2])
            mid = standoff / 2
            parts.strut(f"{name}_hinge_rod", rod(root_top, mid), rod(root_bot, mid),
                        radius=fh["rod_radius"], segments=10, material="dark_metal")
            for i, f in enumerate(fractions):
                z = root_top[2] + (root_bot[2] - root_top[2]) * f
                rb = r_body(z)
                a = rb - 0.1
                parts.box(f"{name}_bracket_{i}", (fh["bracket"], fh["bracket"], standoff + 0.15),
                          location=(ux * (a + (standoff + 0.15) / 2), uy * (a + (standoff + 0.15) / 2), z),
                          direction=(ux, uy, 0), material=steel)

        # Forward flaps: leeward, 140 degrees apart; root along the nose, bottom edge level.
        ff = P["forward_flap"]
        zb = top - ff["bottom_below_tip"]
        zt = zb + ff["root_chord"]
        so = fh["forward_standoff"]
        for a, tag in ((180 - 70, "left"), (180 + 70, "right")):
            ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
            rt, rb = r_at(zt) + so, r_at(zb) + so
            top_pt, bot_pt = (ux * rt, uy * rt, zt), (ux * rb, uy * rb, zb)
            chord = math.dist(top_pt, bot_pt)
            cd = tuple((b - t) / chord for t, b in zip(top_pt, bot_pt))
            rtip = r_at(zb) + ff["span"]
            tip_bot = (ux * rtip, uy * rtip, zb)
            tip_le = tuple(b - dd * ff["tip_chord"] for b, dd in zip(tip_bot, cd))
            flap = parts.surface(f"ship_forward_flap_{tag}", root_le=top_pt, root_chord=chord,
                                 tip_le=tip_le, tip_chord=ff["tip_chord"], thickness=0.05,
                                 chord_dir=cd, material=tiles_tex)
            tiling.plane_uv(flap, (ux, uy), tile_w, tile_h)
            body_pt = lambda p: (p[0] - ux * so, p[1] - uy * so, p[2])
            hinge(f"ship_forward_flap_{tag}", body_pt(top_pt), body_pt(bot_pt), (ux, uy), so,
                  fh["forward_brackets"], r_at)

        # Aft flaps: +y and -y, root down to the ship's base.
        af = P["aft_flap"]
        so = fh["aft_standoff"]
        for sign, tag in parts.sides():
            flap = parts.surface(f"ship_aft_flap_{tag}",
                                 root_le=(0, sign * (R + so), z0 + af["root_chord"]),
                                 root_chord=af["root_chord"],
                                 tip_le=(0, sign * (R + af["span"]), z0 + af["tip_chord"]),
                                 tip_chord=af["tip_chord"], thickness=0.04, chord_dir=(0, 0, -1),
                                 material=tiles_tex)
            tiling.plane_uv(flap, (0, sign), tile_w, tile_h)
            hinge(f"ship_aft_flap_{tag}", (0, sign * R, z0 + af["root_chord"] - 0.3),
                  (0, sign * R, z0 + 0.3), (0, sign), so, fh["aft_brackets"], lambda z: R)
            # Actuator cover over the top of the flap's root: a slim steel wedge sloping down
            # from the body to the root, the flap's top corner inside it.
            hz = P["aft_flap_housing"]
            out = hz["stands_out"] + 0.1
            ub_, uo = (0.0, 1.0) if sign > 0 else (1.0, 0.0)
            parts.outline_plate(f"ship_aft_flap_housing_{tag}",
                                [(ub_, 0), (uo, 0), (uo, hz["outer_height"] / hz["height"]), (ub_, 1)],
                                out, hz["height"], hz["width"],
                                location=(-hz["width"] / 2, sign * (R - 0.1 + out / 2),
                                          z0 + af["root_chord"] - hz["outer_height"] + hz["height"] / 2),
                                direction=(1, 0, 0), up=(0, 0, 1), material=steel)

        # Catch pins on the forward section, either side of the tower side (from_photos.catch_pins).
        cp = P["catch_pins"]
        zp = top - cp["below_tip"]
        for a, tag in ((180 - cp["from_tower_deg"], "left"), (180 + cp["from_tower_deg"], "right")):
            parts.cylinder(f"ship_catch_pin_{tag}", cp["diameter"] / 2, cp["stands_out"] + 0.2,
                           location=_at(a, R - 0.2, zp), direction=_at(a, 1, 0), segments=20,
                           material=steel)

        # Raceways down the leeward side: two steel covers with pointed tops
        # (from_photos.raceways).
        rw = P["raceways"]
        z_lo, z_hi = top - rw["bottom_below_tip"], top - rw["top_below_tip"]
        tip = rw["point_length"] / (z_hi - z_lo)
        for i, a in enumerate(rw["angles_deg"]):
            parts.outline_plate(f"ship_raceway_{i}", [(0, 0), (1, 0), (1, 1 - tip), (0.5, 1), (0, 1 - tip)],
                                rw["width"], z_hi - z_lo, rw["stands_out"] + 0.05,
                                location=_at(a, R - 0.05, (z_lo + z_hi) / 2), direction=_at(a, 1, 0),
                                up=(0, 0, 1), material=steel)

        # Square tile patches on the bare steel, mirrored about the tower side
        # (from_photos.tile_patches): slices of a slightly bigger cylinder, tiles standing proud.
        tp = P["tile_patches"]
        for i, p in enumerate(tp["patches"]):
            for s in (1, -1):
                a = 180 + s * p["from_tower_deg"]
                zc = top - p["below_tip"]
                rr = R + tp["stands_out"]
                patch = parts.lathe(f"ship_tile_patch_{i}_{'l' if s > 0 else 'r'}",
                                    [(0, zc - p["height"] / 2), (rr, zc - p["height"] / 2),
                                     (rr, zc + p["height"] / 2), (0, zc + p["height"] / 2)],
                                    segments=6, sweep_deg=math.degrees(p["width"] / R), roll_deg=a,
                                    smooth=False, material=tiles_tex)
                tiling.cyl_uv(patch, tile_w, tile_h, R)

        # Aft skirt, leeward half (from_photos.aft_skirt): fine vertical ribs up to a band of
        # slotted hardware with coloured fittings, as repeating textures on sheets over the steel.
        ak = P["aft_skirt"]
        a0, a1 = 180 - ak["half_width_deg"], 180 + ak["half_width_deg"]
        rb = ak["ribs"]
        w = 32
        u = (np.arange(w) + 0.5) / w * rb["period"]
        k = np.clip(np.abs(u - rb["period"] / 2) / (rb["line"] / 2), 0, 1)
        shade = rb["darken"] + (1 - rb["darken"]) * (1 - (k < 1))
        rib_img = tiling.image("starship", "aft_skirt_ribs",
                               (_rgb(sm[steel])[None, None] * shade[None, :, None] * np.ones((8, 1, 1))).astype(np.float32),
                               "sRGB")
        rib_mat = materials.image("aft_skirt_ribs", rib_img, metallic=sm[steel]["metallic"],
                                  roughness=sm[steel]["roughness"])
        ribs = _sheet("ship_aft_skirt_ribs", R + 0.01, a0, a1, z0 + ak["ribs_from"], ak["band_bottom"], rib_mat)
        uvl = ribs.data.uv_layers.active.data
        for li in range(len(uvl)):
            uu, vv = uvl[li].uv
            uvl[li].uv = (uu / rb["period"], vv / 1.0)

        hb_ = ak["band"]
        ppm = 200
        bw, bh = hb_["slot_period"] * 3, ak["band_top"] - ak["band_bottom"]
        W, H = int(round(bw * ppm)), int(round(bh * ppm))
        X = (np.arange(W) + 0.5) / ppm
        Y = (np.arange(H) + 0.5) / ppm
        XX, YY = np.meshgrid(X, Y)
        col = {n: _rgb(sm[n]) for n in ("aft_fitting_red", "aft_fitting_gold", "aft_hardware_dark")}
        cyc = [col["aft_fitting_red"], col["aft_fitting_gold"], _rgb(sm[steel])]
        img = np.broadcast_to(_rgb(sm[steel]), (H, W, 3)).copy()
        slot = (XX // hb_["slot_period"]).astype(int)
        xin = XX % hb_["slot_period"] - hb_["slot_period"] / 2
        top0 = bh - hb_["rim"]
        img[YY < hb_["bottom_rim"]] = col["aft_hardware_dark"]
        rim = YY >= top0
        img[rim] = col["aft_hardware_dark"]
        for i in range(3):
            m = rim & (slot == i) & (np.abs(xin) < hb_["stripe_width"] / 2)
            img[m] = cyc[i]
            s_ = (slot == i) & (np.abs(xin) < hb_["slot_width"] / 2) & (YY > hb_["slot_from"]) & (YY < top0 - 0.12)
            img[s_] = col["aft_hardware_dark"]
            cap = s_ & (YY > top0 - 0.12 - hb_["cap"])
            img[cap] = cyc[(i + 1) % 3]
        band_img = tiling.image("starship", "aft_hardware_band", img.astype(np.float32), "sRGB")
        band_mat = materials.image("aft_hardware_band", band_img, metallic=sm["aft_hardware_dark"]["metallic"],
                                   roughness=sm["aft_hardware_dark"]["roughness"])
        band = _sheet("ship_aft_hardware_band", R + hb_["stands_out"], a0, a1, ak["band_bottom"],
                      ak["band_top"], band_mat)
        uvl = band.data.uv_layers.active.data
        for li in range(len(uvl)):
            uu, vv = uvl[li].uv
            uvl[li].uv = (uu / bw, vv / bh)
        # Edges of the band, standing out from the skin.
        for z_, tag in ((ak["band_bottom"], "bottom"), (ak["band_top"], "top")):
            parts.lathe(f"ship_aft_band_edge_{tag}",
                        [(0, z_ - 0.03), (R + hb_["stands_out"] + 0.01, z_ - 0.03),
                         (R + hb_["stands_out"] + 0.01, z_ + 0.03), (0, z_ + 0.03)],
                        segments=32, sweep_deg=2 * ak["half_width_deg"], roll_deg=180, smooth=False,
                        material="aft_hardware_dark")

        # Fittings at the aft end like the catch pins, mirrored about the tower side
        # (from_photos.aft_fittings).
        afp = P["aft_fittings"]
        for a, tag in ((180 - afp["from_tower_deg"], "left"), (180 + afp["from_tower_deg"], "right")):
            parts.cylinder(f"ship_aft_fitting_{tag}", afp["diameter"] / 2, afp["stands_out"] + 0.2,
                           location=_at(a, R - 0.2, afp["z"]), direction=_at(a, 1, 0), segments=20,
                           material=steel)

        # Vents and ports: dark round (and one square) openings as cut-out decals on the skin
        # (from_photos.ports).
        dark = materials.colour(sm["port"])
        mats = {}
        for shape in ("round", "square"):
            im = textures.marking(f"port_{shape}", [(os.path.join(HARNESS, "refs", "starship", f"port_{shape}.png"), dark)], OUT)
            mats[shape] = materials.image(f"port_{shape}", im, metallic=sm["port"]["metallic"],
                                          roughness=sm["port"]["roughness"], cutout=True)
        for i, p in enumerate(P["ports"]["list"]):
            z = top - p["below_tip"]
            a = math.radians(p["deg"])
            rz = r_at(z)
            parts.decal(f"ship_port_{i:02d}", body, center=(rz * math.cos(a), rz * math.sin(a), z),
                        direction=(-math.cos(a), -math.sin(a), 0), up=(0, 0, 1),
                        width=p["size"], height=p["size"], material=mats[p.get("shape", "round")],
                        lift=p.get("lift", 0.002))
