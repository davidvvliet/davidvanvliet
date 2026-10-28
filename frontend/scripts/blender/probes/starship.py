# Starship V3, full stack. Built from lib/parts in metres; every number comes from
# specs/starship.json ("dimensions", "facts", "from_photos", each with its source).
# Frame: z up, engine bell exits at z = 0, axis on x = y = 0; +x is the ship's windward
# (heat-shield) side, away from the tower.
import math
from lib import parts

def _at(angle_deg, r, z):
    a = math.radians(angle_deg)
    return (r * math.cos(a), r * math.sin(a), z)

def build(spec):
    D = {k: v["value"] for k, v in spec["dimensions"].items()}
    F = {k: v["value"] for k, v in spec["facts"].items()}
    P = {k: v["value"] for k, v in spec["from_photos"].items()}
    R = D["diameter_booster"] / 2
    top = D["stack_height"]
    hb = D["booster_height"]
    hs = D["ship_height"]
    steel, tiles = "stainless_steel", "heat_shield_tiles"

    # --- Super Heavy -------------------------------------------------------------------
    with parts.assembly("booster", core=True):
        aft = P["booster_engines_below_skirt"]
        ring_h = P["hot_stage_ring_height"]
        tank_top = hb - ring_h
        parts.cylinder("booster_tank", R, tank_top - aft, location=(0, 0, aft), segments=64,
                       material=steel)

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

        # Grid fins: three, in a T (90/90/180): +y, -y and the heat-shield side (+x).
        gf = P["grid_fin"]
        zc = hb - gf["top_below_booster_top"] - gf["thickness"] / 2
        for a, tag in ((90, "left"), (-90, "right"), (0, "windward")):
            parts.box(f"grid_fin_{tag}", (gf["stands_out"] + 0.1, gf["width"], gf["thickness"]),
                      location=_at(a, R + gf["stands_out"] / 2 - 0.05, zc), roll_deg=a,
                      material="grid_fin")

    # --- Starship ----------------------------------------------------------------------
    with parts.assembly("ship"):
        z0 = top - hs                       # ship base, on the hot-stage ring
        L = P["nose_length"]
        z_nose = top - L
        rho = (R * R + L * L) / (2 * R)     # tangent ogive

        def r_at(z):
            s = z - z_nose
            return R if s <= 0 else max(0.0, math.sqrt(rho * rho - s * s) + R - rho)

        prof = [(0, z0), (R, z0), (R, z_nose)]
        prof += [(r_at(z_nose + L * t), z_nose + L * t) for t in [i / 12 for i in range(1, 12)]]
        prof += [(0.35, top - 0.08), (0, top)]   # blunt tip
        # Windward half black tiles, leeward half bare steel (facts.heat_shield).
        parts.lathe("ship_windward", prof, segments=32, sweep_deg=180, roll_deg=0,
                    material=tiles)
        parts.lathe("ship_leeward", prof, segments=32, sweep_deg=180, roll_deg=180,
                    material=steel)

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
            parts.surface(f"ship_forward_flap_{tag}", root_le=top_pt, root_chord=chord,
                          tip_le=tip_le, tip_chord=ff["tip_chord"], thickness=0.05,
                          chord_dir=cd, material=tiles)

        # Aft flaps: +y and -y, root down to the ship's base.
        af = P["aft_flap"]
        for sign, tag in parts.sides():
            parts.surface(f"ship_aft_flap_{tag}",
                          root_le=(0, sign * (R - 0.05), z0 + af["root_chord"]),
                          root_chord=af["root_chord"],
                          tip_le=(0, sign * (R + af["span"]), z0 + af["tip_chord"]),
                          tip_chord=af["tip_chord"], thickness=0.04, chord_dir=(0, 0, -1),
                          material=tiles)
