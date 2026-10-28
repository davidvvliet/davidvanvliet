# Starship V3, the ship (upper stage). Built from lib/parts in metres; every number comes from
# specs/starship.json ("dimensions", "facts", "from_photos", each with its source).
# Frame: z up, the ship's base (aft skirt) at z = 0, axis on x = y = 0; +x is the windward
# (heat-shield) side, away from the tower. The booster is its own model (superheavy).
import math
from lib import materials, parts, tiling

def build(spec):
    D = {k: v["value"] for k, v in spec["dimensions"].items()}
    F = {k: v["value"] for k, v in spec["facts"].items()}
    P = {k: v["value"] for k, v in spec["from_photos"].items()}
    R = D["diameter"] / 2
    top = D["height"]
    steel, tiles = "stainless_steel", "heat_shield_tiles"
    # Surface detail: hexagonal tiles and weld lines as repeating textures
    # (from_photos.hex_tiles, from_photos.weld_lines, facts.ring_height). A whole number of
    # tile repeats goes round.
    ht = P["hex_tiles"]
    reps = round(2 * math.pi * R / (4 * ht["across_flats"]))
    tile_w = 2 * math.pi * R / reps
    sm = spec["materials"]
    tbase, tnorm, tile_h = tiling.hex_tiles("starship", ht, sm[tiles]["hex"], tile_w)
    tiles_tex = materials.image("heat_shield_tiles_textured", tbase, tnorm,
                                metallic=sm[tiles]["metallic"], roughness=sm[tiles]["roughness"])
    wl = P["weld_lines"]
    welds = tiling.weld_lines("starship", sm[steel]["hex"], F["ring_height"], wl["line"], wl["darken"])
    steel_tex = materials.image("stainless_steel_textured", welds, metallic=sm[steel]["metallic"],
                                roughness=sm[steel]["roughness"])

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
        tiling.cyl_uv(body, tile_w, tile_h, R)
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
            tiling.plane_uv(flap, (ux, uy), tile_w, tile_h)

        # Aft flaps: +y and -y, root down to the ship's base.
        af = P["aft_flap"]
        for sign, tag in parts.sides():
            flap = parts.surface(f"ship_aft_flap_{tag}",
                                 root_le=(0, sign * (R - 0.05), z0 + af["root_chord"]),
                                 root_chord=af["root_chord"],
                                 tip_le=(0, sign * (R + af["span"]), z0 + af["tip_chord"]),
                                 tip_chord=af["tip_chord"], thickness=0.04, chord_dir=(0, 0, -1),
                                 material=tiles_tex)
            tiling.plane_uv(flap, (0, sign), tile_w, tile_h)
            # Actuator housing on the body at the top of the flap's root.
            hz = P["aft_flap_housing"]
            parts.box(f"ship_aft_flap_housing_{tag}", (hz["width"], hz["stands_out"] + 0.1, hz["height"]),
                      location=(0, sign * (R + hz["stands_out"] / 2 - 0.05),
                                z0 + af["root_chord"] - hz["height"] / 2),
                      material=tiles)
