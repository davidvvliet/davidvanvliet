# Starship V3, the ship (upper stage). Built from lib/parts in metres; every number comes from
# specs/starship.json ("dimensions", "facts", "from_photos", each with its source).
# Frame: z up, the ship's base (aft skirt) at z = 0, axis on x = y = 0; +x is the windward
# (heat-shield) side, away from the tower. The booster is its own model (superheavy).
import math
import bmesh
from mathutils import Vector
from lib import materials, parts, tiling

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
        prof = [(0, bay), (R - wall, bay), (R - wall, z0), (R, z0), (R, z_wrap), (R, z_nose)]
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
            if c.z < bay + 1e-3 and math.hypot(c.x, c.y) < R - wall / 2:
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
        sl = F["raptor_sl_nozzle_exit_m"] / 2
        for i, a in enumerate(en["sl_angles_deg"]):
            ze = en["sl_exit_above_base"]
            parts.lathe(f"ship_engine_sl_{i}", _bell(sl, 0.25, 1.53, bay - ze + 0.05),
                        location=_at(a, en["sl_ring_radius"], ze), segments=24, material="dark_metal")
        rv = en["rvac_exit"] / 2
        for i, a in enumerate(en["rvac_angles_deg"]):
            ze = en["rvac_exit_above_base"]
            parts.lathe(f"ship_engine_vac_{i}", _bell(rv, 0.25, 3.0, bay - ze + 0.05),
                        location=_at(a, en["rvac_ring_radius"], ze), segments=32, material="dark_metal")

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
            # Actuator cover on the body at the top of the flap's root: a steel wedge, its top
            # sloping down outward.
            hz = P["aft_flap_housing"]
            out = hz["stands_out"] + 0.1
            ub_, uo = (0.0, 1.0) if sign > 0 else (1.0, 0.0)
            parts.outline_plate(f"ship_aft_flap_housing_{tag}",
                                [(ub_, 0), (uo, 0), (uo, hz["outer_height"] / hz["height"]), (ub_, 1)],
                                out, hz["height"], hz["width"],
                                location=(-hz["width"] / 2, sign * (R - 0.1 + out / 2),
                                          z0 + af["root_chord"] - hz["height"] / 2),
                                direction=(1, 0, 0), up=(0, 0, 1), material=steel)

        # Catch pins on the forward section, either side of the tower side (from_photos.catch_pins).
        cp = P["catch_pins"]
        zp = top - cp["below_tip"]
        for a, tag in ((180 - cp["from_tower_deg"], "left"), (180 + cp["from_tower_deg"], "right")):
            parts.cylinder(f"ship_catch_pin_{tag}", cp["diameter"] / 2, cp["stands_out"] + 0.2,
                           location=_at(a, R - 0.2, zp), direction=_at(a, 1, 0), segments=20,
                           material=steel)
