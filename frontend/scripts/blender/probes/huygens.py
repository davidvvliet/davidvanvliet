# Huygens, as launched: the entry assembly (front shield, back cover) closed around the descent
# module. z up = the probe's +Xp, origin on the axis at the separation plane (spec facts.frame,
# facts.stations); x = +Yp, y = +Zp. Two assemblies, so Explode takes the descent module out of
# the shell, as the X-15 gives up its engine. Cassini places this model (lib/includes.py).
# Every number comes from specs/huygens.json (with its source) or is marked here as estimated.
import math

from lib import materials, parts, tiling

FOIL_TILE = 0.6  # metres per foil tile


def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    f = {k: v["value"] for k, v in spec["facts"].items()}
    st = f["stations"]
    before = set(parts.collection().all_objects)
    dome = f["profile"]["fore_dome"]

    # Explode: the front shield and the back cover come off the descent module, as at Titan.
    with parts.assembly("front_shield"):
        _front_shield(d, f)
    with parts.assembly("back_cover"):
        _back_cover(f)
    with parts.assembly("descent_module", core=True):
        _fore_dome(f, dome)
        _experiment_platform(f, st, dome)
        _after_cone(f, st)
        _top_platform(f, st)

    # Blankets: crinkled foil (crease sizes estimated by eye from KSC-97pc652, as for Cassini's).
    # On Cassini the carrier's own pass turns blanket_amber into its foil, so only the after
    # cone's silver is done here then.
    sm = spec["materials"]
    names = ["mli_silver"] + ([] if spec.get("included_in") else ["blanket_amber"])
    made = [o for o in parts.collection().all_objects if o not in before]
    foils = {}
    for name in names:
        fb, fn = tiling.crinkled_foil("huygens", f"huygens_{name}_foil", sm[name]["hex"], facet=0.025, tilt_deg=7,
                                      wrinkle=0.12, wrinkle_deg=8, spread=0.06, stretch=1.5,
                                      repeat=(FOIL_TILE, FOIL_TILE), px_per_m=700)
        foils[name] = materials.image(f"huygens_{name}_crinkled", fb, normal=fn, metallic=sm[name]["metallic"],
                                      roughness=sm[name]["roughness"])
    for obj in made:
        if obj.type != "MESH" or not obj.data.materials:
            continue
        mats = obj.data.materials
        hit = [i for i, m in enumerate(mats) if m and m.name in foils]
        for i in hit:
            mats[i] = foils[mats[i].name]
        if hit:
            tiling.box_uv(obj, FOIL_TILE)


def P(c_mm, z):
    return (c_mm[0] / 1000, c_mm[1] / 1000, z)


def radial(a_deg, r, z):
    a = math.radians(a_deg)
    return (r * math.cos(a), r * math.sin(a), z)


def dome_z(dome, r):
    """The fore dome's outer surface at radius r (the profile runs from the rim to the nose)."""
    for (r0, z0), (r1, z1) in zip(dome, dome[1:]):
        if r1 <= r <= r0:
            return z0 + (z1 - z0) * (r0 - r) / (r0 - r1)
    return dome[0][1]


def _sphere_cone(nose_z, nose_r, r_end, n=4):
    # 60 deg half-angle sphere-cone (facts.shield): the cap meets the cone at 30 deg.
    c = nose_z + nose_r
    pts = [(nose_r * math.sin(math.radians(30 * i / n)), c - nose_r * math.cos(math.radians(30 * i / n)))
           for i in range(n + 1)]
    r0, z0 = pts[-1]
    return pts + [(r_end, z0 + (r_end - r0) / math.tan(math.radians(60)))]


def _front_shield(d, f):
    # Carbon shell (60 mm, estimated from Fig 2.2-5's hatching), its gold blanket over the front
    # and the 2 mm Prosial coat on the rear outside the back cover's footprint (facts.shield_rear).
    R = d["shield_diameter"] / 2
    sh = 0.0486
    nose = f["stations"]["shield_nose"]
    rim_z = nose + 0.6205
    t = 0.06
    outer = _sphere_cone(nose, 1.25, R - sh)
    inner = _sphere_cone(nose + t, 1.25 - t, R - sh - t)
    parts.lathe("front_shield", outer + [(R, outer[-1][1] + sh), (R, rim_z), (R - 0.01, rim_z)] + list(reversed(inner)),
                segments=48, material="carbon_dark")
    m = 0.006  # blanket thickness, estimated
    mli = _sphere_cone(nose - m, 1.25 + m, R - sh)
    parts.lathe("front_shield_mli", mli + [(R + m, outer[-1][1] + sh), (R + m, rim_z - 0.02), (R + 0.001, rim_z - 0.02),
                                           (R + 0.001, outer[-1][1] + sh)] + list(reversed(outer)),
                segments=48, material="blanket_amber")
    # the rear (inner) face beyond r 0.895 carries a 2 mm coat
    rc = 0.895
    a, b = inner[-2], inner[-1]
    zin = lambda r: a[1] + (r - a[0]) * (b[1] - a[1]) / (b[0] - a[0])
    coat = [(rc, zin(rc)), (b[0], b[1]), (R - 0.01, rim_z)]
    parts.lathe("front_shield_prosial", coat + [(r - 0.0017, z + 0.001) for r, z in reversed(coat)], closed=True,
                segments=48, material="prosial_white")


def _shell(pts, th):
    # an outer line then the same line `th` inside it, as one closed loop
    inner = []
    for i, (r, z) in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        tr, tz = b[0] - a[0], b[1] - a[1]
        n = math.hypot(tr, tz)
        nr, nz = tz / n, -tr / n          # outward normal of a line running up and in
        inner.append((max(r - th * nr, 0.0), z - th * nz))
    return pts + list(reversed(inner))


def _back_cover(f):
    # Stepped cone (facts.back_cover, Fig 2.2-5), a 20 mm shell under its blanket; three SEPS
    # recesses cut into the lower cone at the SEPS fittings, the DISR bump, two access doors,
    # the PDD break-out patch on the flat top and two antenna caps over the S-band antennas.
    # Recess, bump, door, patch and cap sizes estimated from Fig 2.2-9.
    th = 0.02
    skirt = [(0.895, 0.0), (0.895, 0.1515), (0.85, 0.1965)]
    upper = [(0.70, 0.3907), (0.6249, 0.488), (0.3433, 0.578), (0.1609, 0.61), (0.0, 0.61)]
    parts.lathe("back_cover", _shell(skirt, th), closed=True, segments=48, material="blanket_amber")
    parts.lathe("back_cover_upper", _shell(upper, th), closed=True, segments=48, material="blanket_amber")
    cone = [(0.85, 0.1965), (0.70, 0.3907)]
    gap = 22.0  # degrees of each recess
    seps = f["ring_items"]["seps_fittings_deg"]
    for i, a in enumerate(seps):
        span = (seps[(i + 1) % 3] - a) % 360 - gap
        parts.lathe(f"back_cover_cone_{i + 1}", _shell(cone, th), closed=True, segments=16, sweep_deg=span,
                    roll_deg=a + gap / 2 + span / 2, material="blanket_amber")
        # the recess: a floor on the skirt, a back wall at r 0.70, a side wall each side
        parts.lathe(f"seps_recess_{i + 1}", [(0.70, 0.1965), (0.85, 0.1965), (0.85, 0.1985), (0.702, 0.1985),
                                             (0.702, 0.3907), (0.70, 0.3907)], closed=True, segments=6,
                    sweep_deg=gap, roll_deg=a, material="blanket_amber")
        for s in (-1, 1):
            parts.lathe(f"seps_recess_{i + 1}_{'ab'[s > 0]}", [(0.70, 0.1965), (0.85, 0.1965), (0.70, 0.3907)],
                        closed=True, segments=1, sweep_deg=0.6, roll_deg=a + s * (gap / 2 - 0.3),
                        material="blanket_amber")
    # DISR cover bump on the lower cone over the DISR head (+y)
    slope = math.atan2(0.85 - 0.70, 0.3907 - 0.1965)   # the lower cone's lean from the axis
    n = (0.0, math.cos(slope), math.sin(slope))
    parts.box("disr_cover", (0.22, 0.20, 0.05), location=(0.0, 0.78, 0.28), direction=n, material="blanket_amber")
    # two access doors on the middle cone, panels standing proud
    mid = math.atan2(0.6249 - 0.3433, 0.578 - 0.488)
    for i, ad in enumerate((200, 20)):
        u = math.radians(ad)
        n = (math.cos(u) * math.cos(mid), math.sin(u) * math.cos(mid), math.sin(mid))
        parts.box(f"back_cover_door_{i + 1}", (0.16, 0.12, 0.012), location=radial(ad, 0.49, 0.534),
                  direction=n, roll_deg=ad + 90, material="blanket_amber")
    parts.cylinder("pdd_patch", radius=0.11, length=0.008, location=(0, 0, 0.608), segments=16, material="blanket_amber")
    for i, an in enumerate(f["top_platform_items"]["antennas"]):
        x, y = an["centre_mm"][0] / 1000, an["centre_mm"][1] / 1000
        r = math.hypot(x, y)
        z = (0.61 - (r - 0.1609) / (0.3433 - 0.1609) * 0.032) if r < 0.3433 else 0.578 - (r - 0.3433) / 0.2816 * 0.09
        parts.lathe(f"antenna_cap_{i + 1}", [(0.0, 0.0), (0.05, 0.0), (0.045, 0.02), (0.03, 0.035), (0.0, 0.042)],
                    location=(x, y, z - 0.006), segments=12, material="blanket_amber")


def _fore_dome(f, dome):
    # Aluminium fore dome (Fig 2.2-6 profile; a solid, its inside closed by the ring), 36 spin vanes and the
    # openings for the SSP, GCMS and ACP (facts.dome_inlets).
    parts.lathe("fore_dome", [(0.0, 0.0), (dome[0][0], 0.0)] + dome[1:], segments=64, material="fore_dome_gold")
    v = f["spin_vanes"]
    rc = dome_z_radius(dome, v["z"]) + v["height"] / 2 - 0.004
    for i in range(v["count"]):
        a = 2 * math.pi * (i + 0.5) / v["count"]
        u = (math.cos(a), math.sin(a), 0.0)
        # a plate in the plane of the radius and the axis, canted about the radius
        parts.box(f"spin_vane_{i + 1}", (0.003, v["chord"], v["height"]), location=(rc * u[0], rc * u[1], v["z"]),
                  direction=u, roll_deg=v["cant_deg"], material="fore_dome_gold")
    for name, e in f["dome_inlets"].items():
        x, y = e["centre_mm"][0] / 1000, e["centre_mm"][1] / 1000
        zz = dome_z(dome, math.hypot(x, y))
        parts.cylinder(f"{name}_inlet_rim", radius=e["radius_m"] + 0.012, length=0.012, location=(x, y, zz - 0.008),
                       segments=16, material="platform_aluminium")
        parts.cylinder(f"{name}_inlet", radius=e["radius_m"], length=0.004, location=(x, y, zz - 0.010),
                       segments=16, material="dark_metal")


def dome_z_radius(dome, z):
    """The fore dome's radius at height z."""
    for (r0, z0), (r1, z1) in zip(dome, dome[1:]):
        if z1 <= z <= z0:
            return r0 + (r1 - r0) * (z0 - z) / (z0 - z1)
    return dome[0][0]


def _unit(name, e, z_face, down=False, h=None):
    h = e["height_m"] if h is None else h
    x, y = e["centre_mm"][0] / 1000, e["centre_mm"][1] / 1000
    zc = z_face - h / 2 if down else z_face + h / 2
    return parts.box(name, (e["size_mm"][0] / 1000, e["size_mm"][1] / 1000, h), location=(x, y, zc),
                     roll_deg=e["angle_deg"], material=e["material"])


def _experiment_platform(f, st, dome):
    # Central ring and the 73 mm experiment platform (facts.stations), the units on both sides
    # (facts.units_top, units_bottom), the GCMS and SSP through it, and what the ring carries
    # (facts.ring_items).
    p0, p1 = st["experiment_platform"]
    r_in, r_out = f["profile"]["ring"]
    parts.lathe("central_ring", [(r_in, 0.0), (r_out, 0.0), (r_out, st["ring_top"]), (r_in, st["ring_top"])],
                closed=True, segments=64, material="platform_aluminium")
    parts.cylinder("experiment_platform", radius=r_in, length=p1 - p0, location=(0, 0, p0), segments=48,
                   material="platform_aluminium")
    for name, e in f["units_top"].items():
        _unit(name, e, p1)
    for name, e in f["units_bottom"].items():
        if e["height_m"] > 0:
            _unit(name, e, p0, down=True)
    # ACP, SSP and GCMS run down to their dome openings
    acp = f["units_bottom"]["acp"]
    far = math.hypot(*acp["centre_mm"]) / 1000 + 0.13
    _unit("acp", acp, p0, down=True, h=p0 - dome_z(dome, far) - 0.01)
    ssp = f["ssp"]
    x, y = P(ssp["centre_mm"], 0)[:2]
    zb = dome_z(dome, math.hypot(x, y) + ssp["radius_m"]) + 0.004
    parts.cylinder("ssp", radius=ssp["radius_m"], length=p0 - zb, location=(x, y, zb), segments=16, material="unit_black")
    g = f["gcms"]
    x, y = P(g["centre_mm"], 0)[:2]
    ht = g["top_height_m"]
    parts.lathe("gcms", [(0.0, p1), (g["radius_m"], p1), (g["radius_m"], p1 + ht - 0.04),
                         (g["radius_m"] - 0.04, p1 + ht), (0.0, p1 + ht)],
                location=(x, y, 0), segments=24, material="platform_aluminium")
    zb = dome_z(dome, math.hypot(x, y) + 0.11) + 0.004
    parts.cylinder("gcms_lower", radius=0.11, length=p0 - zb, location=(x, y, zb), segments=16, material="platform_aluminium")
    ri = f["ring_items"]
    for i, a in enumerate(ri["seps_fittings_deg"]):
        # titanium column to the top platform (place estimated) and the SEPS fitting on the ring
        parts.cylinder(f"column_{i + 1}", radius=0.015, length=st["top_platform"][0] - p1,
                       location=radial(a + 60, 0.45, p1), segments=12, material="dark_metal")
        parts.box(f"seps_fitting_{i + 1}", (0.07, 0.09, 0.07), location=radial(a, r_out + 0.035, 0.05),
                  roll_deg=a, material="dark_metal")
    ra = ri["radar_antennas"]
    for i, a in enumerate(ra["angles_deg"]):
        u, tilt = math.radians(a), math.radians(ra["tilt_deg"])
        n = (math.cos(u) * math.sin(tilt), math.sin(u) * math.sin(tilt), -math.cos(tilt))
        parts.box(f"radar_antenna_{i + 1}", (ra["side"], ra["side"], 0.02), location=radial(a, ra["r"], 0.0),
                  direction=n, roll_deg=a, material="unit_black")
        parts.strut(f"radar_antenna_mount_{i + 1}", radial(a, r_out - 0.01, 0.02), radial(a, ra["r"], 0.0),
                    radius=0.012, material="dark_metal")
    for i, bm in enumerate(ri["hasi_booms"]):
        h = P(bm["hinge_mm"], 0.05)
        tip = P(bm["tip_mm"], 0.05)
        parts.cylinder(f"hasi_hinge_{i + 1}", radius=0.025, length=0.05, location=(h[0], h[1], 0.025), segments=16,
                       material="dark_metal")
        parts.strut(f"hasi_boom_{i + 1}", h, tip, radius=0.01, material="platform_aluminium")
        parts.lathe(f"hasi_sensor_{i + 1}", [(0.0, -0.045), (0.025, -0.02), (0.025, 0.02), (0.0, 0.045)],
                    location=tip, direction=(tip[0] - h[0], tip[1] - h[1], 0), segments=16, material="platform_aluminium")
    hs = ri["hasi_stud"]
    parts.strut("hasi_stud", radial(hs["angle_deg"], hs["r"][0] - 0.01, 0.05), radial(hs["angle_deg"], hs["r"][1], 0.05),
                radius=0.008, material="platform_aluminium")
    a = math.radians(hs["angle_deg"])
    tx, ty, _ = radial(hs["angle_deg"], hs["r"][1] - 0.02, 0.05)
    parts.strut("hasi_stud_bar", (tx - 0.05 * math.sin(a), ty + 0.05 * math.cos(a), 0.05),
                (tx + 0.05 * math.sin(a), ty - 0.05 * math.cos(a), 0.05), radius=0.006, material="platform_aluminium")
    for i, a in enumerate(ri["dischargers_deg"]):
        parts.strut(f"discharger_{i + 1}", radial(a, r_out - 0.01, 0.06), radial(a, r_out + 0.15, 0.03), radius=0.004,
                    material="dark_metal")
    dh = ri["disr_head"]
    depth = dh["size_mm"][1] / 1000
    parts.box("disr_head", (dh["size_mm"][0] / 1000, depth, dh["height_m"]),
              location=radial(dh["angle_deg"], r_out + depth / 2 - 0.005, 0.03 + dh["height_m"] / 2),
              roll_deg=dh["angle_deg"] - 90, material="unit_black")


def _after_cone(f, st):
    # After cone from the ring to the top platform (Fig 2.2-6) under its silver blanket, with the access door (facts.descent_structure; its size and place estimated).
    pr = f["profile"]["after_cone"]
    # a solid closed under the top platform (the units inside are never seen)
    top = pr[-1][1] - 0.012
    parts.lathe("after_cone", [(0.0, st["ring_top"]), (pr[0][0], st["ring_top"]), pr[1], (pr[-1][0], top), (0.0, top)],
                segments=64, material="mli_silver")
    (r0, z0), (r1, z1) = pr[0], pr[1]
    zc = 0.22
    rc = r0 + (r1 - r0) * (zc - z0) / (z1 - z0)
    s = math.atan2(r0 - r1, z1 - z0)
    u = math.radians(200.0)
    n = (math.cos(u) * math.cos(s), math.sin(u) * math.cos(s), math.sin(s))
    parts.box("after_cone_door", (0.14, 0.12, 0.008), location=radial(200.0, rc, zc), direction=n, roll_deg=290.0,
              material="fore_dome_gold")


def _top_platform(f, st):
    # 25 mm top platform (facts.stations, profile) with the parachute container, mortar (PDD),
    # the two S-band antennas, the three parachute jettison mechanisms, CD-ROM, DIAMOND and the
    # harness run (facts.units_top_platform, top_platform_items).
    z0, z1 = st["top_platform"]
    parts.cylinder("top_platform", radius=f["profile"]["top_platform_radius"], length=z1 - z0, location=(0, 0, z0),
                   segments=64, material="fore_dome_gold")
    for name, e in f["units_top_platform"].items():
        _unit(name, e, z1)
    # the container's lid under gold foil (KSC-97pc652), 1 cm proud of the white wrap
    c = f["units_top_platform"]["parachute_container"]
    _unit("parachute_lid", dict(c, size_mm=[c["size_mm"][0] + 10, c["size_mm"][1] + 10], material="blanket_amber"),
          z1 + c["height_m"], h=0.012)
    tp = f["top_platform_items"]
    pdd = tp["pdd"]
    parts.cylinder("pdd", radius=pdd["radius_m"], length=pdd["height_m"], location=P(pdd["centre_mm"], z1), segments=16,
                   material="webbing_white")
    for i, an in enumerate(tp["antennas"]):
        parts.cylinder(f"s_band_antenna_{i + 1}", radius=tp["antenna_radius_m"], length=tp["antenna_height_m"],
                       location=P(an["centre_mm"], z1), segments=16, material="platform_aluminium")
        parts.box(f"s_band_antenna_base_{i + 1}", (0.12, 0.12, 0.012), location=P(an["centre_mm"], z1 + 0.006),
                  material="platform_aluminium")
    for i, pj in enumerate(tp["pjm"]):
        parts.cylinder(f"pjm_{i + 1}", radius=0.055, length=0.06, location=P(pj["centre_mm"], z1), segments=12,
                       material="platform_aluminium")
        parts.box(f"pjm_{i + 1}_bar", (0.18, 0.03, 0.03), location=P(pj["centre_mm"], z1 + 0.045),
                  roll_deg=pj["angle_deg"], material="dark_metal")
    parts.cylinder("cd_rom", radius=tp["cd_rom"]["radius_m"], length=0.006, location=P(tp["cd_rom"]["centre_mm"], z1),
                   segments=16, material="platform_aluminium")
    parts.cylinder("diamond", radius=tp["diamond"]["radius_m"], length=0.02, location=P(tp["diamond"]["centre_mm"], z1),
                   segments=12, material="platform_aluminium")
    a, b = tp["harness"]
    parts.tube("harness", [P(a, z1 + 0.025), P(b, z1 + 0.025)], radius=0.025, material="webbing_white")
