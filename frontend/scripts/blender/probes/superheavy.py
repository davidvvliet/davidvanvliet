# Super Heavy, Starship V3's booster. Built from lib/parts in metres; every number comes from
# specs/superheavy.json ("dimensions", "facts", "from_photos", each with its source).
# Frame: z up, engine bell exits at z = 0, axis on x = y = 0; +x is the heat-shield side
# of the ship it carries, away from the tower.
import math
from lib import materials, parts, tiling

def _at(angle_deg, r, z):
    a = math.radians(angle_deg)
    return (r * math.cos(a), r * math.sin(a), z)

def build(spec):
    D = {k: v["value"] for k, v in spec["dimensions"].items()}
    F = {k: v["value"] for k, v in spec["facts"].items()}
    P = {k: v["value"] for k, v in spec["from_photos"].items()}
    R = D["diameter"] / 2
    hb = D["height"]
    steel = "stainless_steel"
    sm = spec["materials"]
    wl = P["weld_lines"]
    welds = tiling.weld_lines("superheavy", sm[steel]["hex"], F["ring_height"], wl["line"],
                              wl["darken"])
    steel_tex = materials.image("stainless_steel_textured", welds, metallic=sm[steel]["metallic"],
                                roughness=sm[steel]["roughness"])

    with parts.assembly("booster", core=True):
        aft = P["engines_below_skirt"]
        ring_h = P["hot_stage_ring_height"]
        tank_top = hb - ring_h
        tank = parts.cylinder("booster_tank", R, tank_top - aft, location=(0, 0, aft), segments=64,
                              material=steel_tex)
        tiling.cyl_uv(tank, 1.0, F["ring_height"], R)

        # 33 bells: 3 centre, 10 middle, 20 outer (facts.engine_rings). Bell profile:
        # exit at z = 0, throat 1.53 m up (faa_plume's throat-to-exit length), powerhead into
        # the aft plate.
        ex = P["nozzle_exit"] / 2
        bell = [(0, 0.15), (ex, 0), (ex * 0.85, 0.5), (ex * 0.6, 1.1), (0.25, 1.53),
                (0.4, 1.8), (0.4, aft + 0.2), (0, aft + 0.2)]
        c = F["centre_engine_clocking_deg"]
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
        ch = P["chines"]
        for sign, tag in parts.sides():
            y0, y1 = sign * (R - 0.05), sign * (R + ch["stands_out"])
            z_top = aft + ch["top_above_aft_end"]
            parts.surface(f"booster_chine_{tag}", root_le=(0, y0, z_top), root_chord=z_top - aft,
                          tip_le=(0, y1, z_top - 3.0), tip_chord=z_top - 3.0 - aft,
                          thickness=0.03, chord_dir=(0, 0, -1), material=steel)

        rw = P["raceway"]
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

        # A ribbed band of fittings round the booster (from_photos.band).
        bd = P["band"]
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
