# Super Heavy, Starship V3's booster. Built from lib/parts in metres; every number comes from
# specs/superheavy.json ("dimensions", "facts", "from_photos", each with its source).
# Frame: z up, engine bell exits at z = 0, axis on x = y = 0; +x is the heat-shield side
# of the ship it carries, away from the tower.
import math
from mathutils import Vector
from lib import engines, materials, parts, tiling

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
                              wl["darken"], rings=wl["rings"], shade_spread=wl["shade_spread"])
    steel_tex = materials.image("stainless_steel_textured", welds, metallic=sm[steel]["metallic"],
                                roughness=sm[steel]["roughness"])

    with parts.assembly("booster", core=True):
        aft = P["engines_below_skirt"]
        tank_top = hb - P["hot_stage_crown"]["height"]   # the dome's base, where the struts stand
        tank = parts.cylinder("booster_tank", R, tank_top - aft, location=(0, 0, aft), segments=64,
                              material=steel_tex)
        tiling.cyl_uv(tank, 1.0, F["ring_height"] * wl["rings"], R)

        # 33 Raptors (from_photos.engine, a stand-in until Raptor 3 is modelled): 3 centre,
        # 10 middle, 20 outer (facts.engine_rings), exits at z = 0, hanging from a dark aft
        # plate (from_photos.aft_plate).
        c = F["centre_engine_clocking_deg"]
        centre = [90, 90 + c[0], 90 + c[0] + c[1]]
        rings = [(0.85, centre), (2.4, [18 + 36 * k for k in range(10)]),
                 (3.9, [9 + 18 * k for k in range(20)])]
        k = 0
        for r, angles in rings:
            for a in angles:
                engines.place(P["engine"], f"booster_engine_{k:02d}", location=_at(a, r, 0),
                              roll_deg=a, lod="low")
                k += 1
        parts.cylinder("booster_aft_plate", R - 0.05, 0.05, location=(0, 0, aft - 0.04),
                       segments=64, material="dark_metal")

        # Aft end (from_photos.aft_manifold): a dark rim with square holes, and above it a
        # bundle of tubes round the body held by clamp blocks.
        am = P["aft_manifold"]
        rim1 = aft + am["rim_height"]
        parts.lathe("booster_aft_rim", [(R - 0.05, aft), (R + 0.02, aft), (R + 0.02, rim1),
                                        (R - 0.05, rim1)], closed=True, segments=64, smooth=False,
                    material="dark_metal")
        for i in range(am["rim_holes"]):
            a = 360 * (i + 0.5) / am["rim_holes"]
            h = am["rim_hole"]
            parts.box(f"booster_aft_rim_hole_{i:02d}", (0.02, h, h),
                      location=_at(a, R + 0.025, aft + am["rim_height"] * 0.6), roll_deg=a,
                      material="grid_fin")
        mh, nt, so = am["height"], am["tubes"], am["stands_out"]
        tr = mh / nt / 2
        prof = [(R - 0.02, rim1)]
        for j in range(nt):
            zc = rim1 + tr * (2 * j + 1)
            prof += [(R + so - tr + tr * math.cos(t), zc + tr * math.sin(t))
                     for t in (-math.pi / 2, -math.pi / 4, 0, math.pi / 4)]
        prof += [(R + so - tr, rim1 + mh), (R - 0.02, rim1 + mh)]
        parts.lathe("booster_aft_manifold", prof, closed=True, segments=64, smooth=False,
                    material="dark_metal")
        for i in range(am["clamps"]):
            a = 360 * i / am["clamps"]
            parts.box(f"booster_aft_clamp_{i:02d}",
                      (am["clamp_stands_out"], am["clamp_width"], am["clamp_height"]),
                      location=_at(a, R + so + am["clamp_stands_out"] / 2 - 0.1, rim1 + mh / 2),
                      roll_deg=a, material="dark_metal")

        # Lower-body fairings (from_photos.chines): four box sections 90 degrees apart, their
        # tops chamfered back into the body.
        ch = P["chines"]
        depth = ch["stands_out"] + 0.05
        z_top = aft + ch["top_above_aft_end"]
        h = z_top - aft
        c = ch["top_chamfer"] / h
        for i, a in enumerate(ch["angles_deg"]):
            t = Vector(_at(a + 90, 1, 0))
            mid = Vector(_at(a, R - 0.05 + depth / 2, (aft + z_top) / 2))
            # The plate's u runs inward here (up x tangent), so u = 0 is the outer face.
            parts.outline_plate(f"booster_chine_{i}", [(1, 0), (0, 0), (0, 1 - c), (1, 1)],
                                depth, h, ch["width"], location=tuple(mid - t * ch["width"] / 2),
                                direction=tuple(t), material=steel)

        # Raceway (from_photos.raceway): a narrow cover down the body, swelling at its top into
        # a fairing with a pointed end; two pipes run beside it on clamps, the outer one bending
        # into the tank through a port at the top.
        rw = P["raceway"]
        ra = rw["angle_from_x_deg"]
        f_top = hb - rw["fairing_top_below_top"]
        f_bot = f_top - rw["fairing_length"]
        fw = rw["fairing_width"] / 2
        parts.lathe("booster_raceway_fairing",
                    [(0, f_bot), (rw["width"] / 2, f_bot), (fw, f_bot + rw["fairing_taper"]),
                     (fw, f_top - rw["fairing_point"]), (fw * 0.35, f_top - 0.15), (0, f_top)],
                    location=_at(ra, R + rw["stands_out"] - fw, 0), segments=16, material=steel)
        parts.box("booster_raceway", (rw["stands_out"] + 0.1, rw["width"], f_bot + 0.1 - (aft + 0.4)),
                  location=_at(ra, R + rw["stands_out"] / 2 - 0.05, (aft + 0.4 + f_bot + 0.1) / 2),
                  roll_deg=ra, material=steel)
        pp = rw["pipes"]
        z_lo = aft + 0.4
        for k, (off, dia, top_below) in enumerate(zip(pp["offsets_deg"], pp["diameters"], pp["top_below_top"])):
            a = ra + off
            r_out = R + pp["stands_out"]
            z_hi = hb - top_below
            parts.tube(f"booster_raceway_pipe_{k}",
                       [_at(a, r_out, z_lo), _at(a, r_out, z_hi), _at(a, R - 0.05, z_hi)],
                       dia / 2, segments=10, bend_radius=0.3, material=steel)
            z = z_hi - pp["clamp_spacing"]
            while z > z_lo + 0.3:
                parts.box(f"booster_raceway_clamp_{k}_{int(round(z * 10)):04d}",
                          (pp["stands_out"] + 0.05, 0.12, 0.15),
                          location=_at(a, R + pp["stands_out"] / 2 - 0.02, z), roll_deg=a,
                          material="grid_fin")
                z -= pp["clamp_spacing"]

        # Integrated hot stage: the methane tank's exposed dome inside a crown of V struts
        # that carries a ring the ship stands on.
        hsr = P["hot_stage_struts"]
        dh = hsr["dome_height"]
        dome = [(R, 0)] + [(R * math.cos(t), dh * math.sin(t))
                           for t in [math.radians(x) for x in range(15, 90, 15)]] + [(0, dh)]
        parts.lathe("booster_dome", dome, location=(0, 0, tank_top - 0.01), segments=48,
                    material=steel)
        # Top ring: a flat band the ship stands on (from_photos.hot_stage_crown).
        cr = P["hot_stage_crown"]
        ring_t, band_t = cr["ring_height"], cr["ring_thickness"]
        parts.lathe("hotstage_ring", [(R - band_t, hb - ring_t), (R, hb - ring_t), (R, hb),
                                      (R - band_t, hb)], closed=True, segments=64, smooth=False,
                    material=steel)
        # V struts: round tubes tapering at both ends, each pair's feet meeting in a bracket on
        # the tank's top edge, their heads spread round the ring.
        n = hsr["v_pairs"]
        sr = hsr["strut_diameter"] / 2
        re_ = cr["strut_end_diameter"] / 2
        r_axis = R - sr - 0.02
        for i in range(n):
            a = 360 * i / n
            foot = Vector(_at(a, r_axis, tank_top + cr["foot_above_tank_top"]))
            for j, da in enumerate((-180 / n, 180 / n)):
                head = Vector(_at(a + da, r_axis, hb - ring_t / 2))
                L = (head - foot).length
                tb, tt = cr["taper_bottom"], cr["taper_top"]
                parts.lathe(f"hotstage_strut_{i:02d}_{j}",
                            [(0, 0), (re_, 0), (sr, tb), (sr, L - tt), (re_, L), (0, L)],
                            location=tuple(foot), direction=tuple(head - foot), segments=10,
                            material=steel)
            # Bracket under the feet: a dark fork, or a steel box on a gold base
            # (from_photos.hot_stage_crown.brackets).
            br = cr["bracket"]
            z_top = tank_top + cr["foot_above_tank_top"] + 0.05
            out = Vector(_at(a, 1, 0))
            side = Vector((-out.y, out.x, 0))
            c = Vector(_at(a, R + br["depth"] / 2 - 0.05, z_top - br["height"] / 2))
            if round(a) in cr["steel_brackets_deg"]:
                parts.box(f"hotstage_bracket_{i:02d}", (br["depth"], br["width"], br["height"] - br["base"]),
                          location=tuple(c + Vector((0, 0, br["base"] / 2))), roll_deg=a, material=steel)
                parts.box(f"hotstage_bracket_{i:02d}_base", (br["depth"], br["width"], br["base"]),
                          location=tuple(c - Vector((0, 0, (br["height"] - br["base"]) / 2))), roll_deg=a,
                          material="bracket_gold")
            else:
                for k, sgn in enumerate((-1, 1)):
                    parts.box(f"hotstage_bracket_{i:02d}_{k}", (br["depth"], br["prong"], br["height"]),
                              location=tuple(c + side * sgn * (br["width"] - br["prong"]) / 2),
                              roll_deg=a, material="grid_fin")
                parts.box(f"hotstage_bracket_{i:02d}_top", (br["depth"], br["width"], br["prong"]),
                          location=tuple(c + Vector((0, 0, br["height"] / 2 - br["prong"] / 2))),
                          roll_deg=a, material="grid_fin")

        # Round ports in octagonal plates below the crown (from_photos.crown_ports).
        cp = P["crown_ports"]
        for i, a in enumerate(cp["angles_deg"]):
            z = tank_top - cp["below_tank_top"]
            parts.prism(f"booster_port_plate_{i}", 8, cp["plate_diameter"] / 2, 0.04,
                        location=_at(a, R - 0.01, z), direction=_at(a, 1, 0), roll_deg=22.5,
                        material=steel)
            parts.cylinder(f"booster_port_{i}", cp["port_diameter"] / 2, 0.1,
                           location=_at(a, R, z), direction=_at(a, 1, 0), segments=20,
                           material="grid_fin")

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
            # The fin turns on a round, geared mount on the body (from_photos.grid_fin_mount).
            gm = P["grid_fin_mount"]
            parts.cylinder(f"grid_fin_{tag}_mount", gm["diameter"] / 2, gm["stands_out"] + 0.05,
                           location=_at(a, R - 0.05, zc), direction=_at(a, 1, 0), segments=32,
                           material="grid_fin")
