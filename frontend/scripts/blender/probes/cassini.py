# Cassini-Huygens, as launched: Huygens attached, magnetometer boom and RPWS antennas deployed.
# Built in the frame of NASA's model A (refs/cassini/reference-sheet.png) so the sheets overlay:
# z up with the dish on top, Huygens toward +x, magnetometer boom toward +y. That is the
# spacecraft frame turned 180 degrees about Y (spec note). Metres. Checked sizes come from the
# spec's `dimensions`; positions and sizes no document gives come from `from_reference_model`
# (measured on model A), every z stretched so the stack is the documented 6.8 m.
import math
from lib import materials, parts, tiling

def _along(start, direction, s):
    return tuple(start[i] + direction[i] * s for i in range(3))

def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    ref = {k: v["value"] for k, v in spec["from_reference_model"].items() if isinstance(v, dict) and "value" in v}
    k = ref["z_stretch"]
    Z = lambda z: z * k
    P = lambda p: (p[0], p[1], Z(p[2]))

    # High-gain antenna (facts.hga_optics): paraboloid with F = 1315 mm and D = 4000 mm, so
    # D^2/16F deep (hga_depth), its rim where NASA's assembly model has it; opening up (+z).
    hg = ref["hga"]
    R = d["hga_diameter"] / 2
    depth = d["hga_depth"]
    F = R * R / (4 * depth)
    vertex = Z(hg["rim_z"] - depth)
    surf = lambda r: vertex + r * r / (4 * F)          # dish surface height at radius r
    with parts.assembly("hga"):
        parts.dish("hga", diameter=d["hga_diameter"], depth=depth, location=(0, 0, vertex), material="hga_white")
        # Back structure (NASA assembly model): six radial ribs in two segments each and a
        # stiffening ring, on the back of the shell.
        rb = hg["ribs"]
        for i, az in enumerate(rb["azimuths_deg"]):
            c, s = math.cos(math.radians(az)), math.sin(math.radians(az))
            for j, (r0, z0, r1, z1, rad) in enumerate(rb["segments"]):
                # NASA's shell is thicker than ours: hang each rib just under our 20 mm shell.
                z0, z1 = (min(Z(z), surf(r) - 0.02 - rad) for r, z in ((r0, z0), (r1, z1)))
                parts.strut(f"hga_rib_{i + 1}_{j + 1}", (r0 * c, r0 * s, z0), (r1 * c, r1 * s, z1),
                            radius=rad, material="hga_white")
        rg = hg["ring"]
        g0, g1 = Z(rg["z"][0]) - 0.021, Z(rg["z"][1]) - 0.021       # under our shell too
        parts.lathe("hga_ring", [(rg["r"][0], g0), (rg["r"][1], g0), (rg["r"][1], g1), (rg["r"][0], g1)],
                    closed=True, segments=64, material="hga_white")
        # Six-strut CFRP tripod (facts.hga_optics): from three feet on the dish, each foot to the
        # two nearest corners of the subreflector deck.
        tp = hg["tripod"]
        for i, az in enumerate(tp["foot_azimuths_deg"]):
            fa = math.radians(az)
            foot = (tp["foot_r"] * math.cos(fa), tp["foot_r"] * math.sin(fa), Z(tp["foot_z"]))
            for j, side in enumerate((-60, 60)):
                ta = math.radians(az + side)
                parts.strut(f"hga_tripod_{i + 1}_{j + 1}", foot,
                            (tp["top_r"] * math.cos(ta), tp["top_r"] * math.sin(ta), Z(tp["top_z"])),
                            radius=tp["radius"], material="dark_metal")
        # Subreflector and Kevlar deck with the S-band feed and LGA1, and the X/Ku/Ka feed
        # cluster at the Cassegrain focus: copied from NASA's assembly model (no document gives
        # their shape; refs/cassini/meshes, cut with run.py cut, see from_reference_model.meshes).
        parts.mesh_file("hga_deck", "refs/cassini/meshes/hga_deck.json", material="hga_white")
        parts.mesh_file("hga_feed", "refs/cassini/meshes/hga_feed.json", material="hga_white")

    # Upper equipment module: the 12-bay electronics bus (facts.bus), bay 1 on spacecraft +X
    # (our -x), under its blanket (PIA04603); bay panels where NASA's assembly model has them.
    bus = ref["bus"]
    b0, b1 = Z(bus["z"][0]), Z(bus["z"][1])
    n = bus["sides"]
    corner = bus["apothem"] / math.cos(math.pi / n)
    hs = ref["hga_support"]
    h0, h1 = Z(hs["z"][0]), Z(hs["z"][1])
    with parts.assembly("bus", core=True):
        parts.prism("bus", sides=n, radius=corner, height=b1 - b0, location=(0, 0, b0),
                    roll_deg=180 / n, material="blanket_amber")
        parts.cylinder("bus_cover", radius=bus["apothem"] * 0.98, length=0.03, location=(0, 0, b1), segments=n * 3,
                       material="blanket_amber")
        # Louvres, connectors and brackets on the bay faces, and the struts, bipods and brackets
        # between the bus top and the dish support: copied from NASA's assembly model.
        parts.mesh_file("bus_faces", "refs/cassini/meshes/bus_faces.json", material="foil_silver")
        parts.mesh_file("bus_upper", "refs/cassini/meshes/bus_upper.json", material="foil_silver")
        # The cylinder under the dish and its bottom plate (NASA assembly model).
        parts.cylinder("hga_support", radius=hs["radius"], length=h1 - h0,
                       location=(0, 0, h0), segments=48, material="white_paint")
        parts.cylinder("hga_support_plate", radius=hs["plate_radius"], length=hs["plate_thickness"],
                       location=(0, 0, Z(hs["plate_z"])), segments=48, material="white_paint")
        # Propulsion module under its blanket, and the lower equipment module below it.
        # The blanket wrapped over the tanks and the black blanket panels on its +-y sides, as
        # flown: copied from NASA model A (no document gives the tank or blanket sizes, and the
        # assembly model has no tanks).
        parts.mesh_file("prop_module", "refs/cassini/meshes/prop_blanket.json", material="blanket_amber")
        parts.mesh_file("prop_black", "refs/cassini/meshes/prop_black.json", material="blanket_black")
        # Lower equipment module under its black blanket (NASA model A).
        parts.mesh_file("lem", "refs/cassini/meshes/lem.json", material="blanket_black")

    # Main engine assembly (facts.main_engines): the two engines with their gimbals and
    # actuators under the thrust plate, copied from NASA's assembly model, nozzles down.
    with parts.assembly("engines"):
        parts.mesh_file("engines", "refs/cassini/meshes/engines.json", material="foil_silver")

    # Three RTGs at the base, radial (facts.rtg_count), each with its mount and its black shade
    # above it: copied from NASA's assembly model (GPHS-RTG with its eight fins, facts.rtg_fins;
    # checked against the documents by rtg_length and rtg_fin_span).
    for i in range(3):
        with parts.assembly(f"rtg_{i + 1}"):
            parts.mesh_file(f"rtg_{i + 1}", f"refs/cassini/meshes/rtg_{i + 1}.json", material="dark_metal")
            parts.mesh_file(f"rtg_mount_{i + 1}", f"refs/cassini/meshes/rtg_mount_{i + 1}.json", material="foil_silver")
            parts.mesh_file(f"rtg_shade_{i + 1}", f"refs/cassini/meshes/rtg_shade_{i + 1}.json", material="blanket_black")

    # Four RCS thruster clusters (facts.rcs_clusters) at the ends of their arms: the clusters
    # from NASA's assembly model, the arms under their gold blankets from model A.
    for i in range(4):
        with parts.assembly(f"rcs_{i + 1}"):
            parts.mesh_file(f"rcs_{i + 1}", f"refs/cassini/meshes/rcs_{i + 1}.json", material="foil_silver")
            parts.mesh_file(f"rcs_arm_{i + 1}", f"refs/cassini/meshes/rcs_arm_{i + 1}.json", material="blanket_amber")

    # Huygens on +x (spacecraft -X), in its launch configuration (huygens_um Fig 2.2-5), as three
    # assemblies so Explode takes it apart: front shield facing out, descent module inside,
    # back cover toward the orbiter. Profiles are (r, h) in metres, h up the probe's +Xp axis
    # from the separation plane, which runs toward the orbiter (our -x).
    hy = ref["huygens"]
    Rh = d["huygens_diameter"] / 2
    sep = ref["huygens_nose_x"] - 0.375          # nose 375 mm below the separation plane
    hc = (sep, hy["centre"][1], Z(hy["centre"][2]))
    out = (-1, 0, 0)                             # +Xp in our frame

    def sphere_cone(nose_h, nose_r, r_end, n=8):
        # 60 deg half-angle sphere-cone (facts.huygens_shield): the cap meets the cone at 30 deg.
        c = nose_h + nose_r
        pts = [(nose_r * math.sin(math.radians(30 * i / n)), c - nose_r * math.cos(math.radians(30 * i / n)))
               for i in range(n + 1)]
        r0, h0 = pts[-1]
        return pts + [(r_end, h0 + (r_end - r0) / math.tan(math.radians(60)))]

    # Front shield: R1250 nose, 620.5 mm from the nose to the rim (Fig 2.2-5); the shell
    # thickness (60 mm) is estimated from the drawing's hatching.
    t = 0.06
    rim_h = 0.6205 - 0.375
    outer = sphere_cone(-0.375, 1.25, Rh - 0.0486)
    inner = sphere_cone(-0.375 + t, 1.25 - t, Rh - 0.0486 - t)
    with parts.assembly("huygens_shield", within="huygens"):
        parts.lathe("huygens_shield", outer + [(Rh, outer[-1][1] + 0.0486), (Rh, rim_h), (Rh - 0.01, rim_h)]
                    + list(reversed(inner)), location=hc, direction=out, segments=64, material="blanket_amber")

    # Descent module (Fig 2.2-6): fore dome 272 deep, experiment platform ring (73 thick, 1.3 m
    # across, huygens_platform_diameter), after cone to the top platform, 636 overall. Dome and
    # after-cone radii and its place in the shell (dome 257 mm below the plane, Fig 2.2-5) are estimated.
    dm0, dome_r = -0.257, 0.62
    dome = [(dome_r * math.sqrt(1 - (1 - i / 8) ** 2), dm0 + 0.272 * i / 8) for i in range(9)]
    with parts.assembly("huygens_descent", within="huygens"):
        parts.lathe("huygens_descent", dome + [(0.64, dm0 + 0.345), (0.56, dm0 + 0.636), (0, dm0 + 0.636)],
                    location=hc, direction=out, segments=48, material="foil_silver")
        parts.lathe("huygens_ring", [(0.60, dm0 + 0.272), (0.65, dm0 + 0.272), (0.65, dm0 + 0.345),
                                     (0.60, dm0 + 0.345)], closed=True, location=hc, direction=out,
                    segments=48, material="foil_silver")
        # 36 spin vanes on the fore dome's periphery (facts.huygens_descent); size and cant estimated.
        for i in range(36):
            a = 2 * math.pi * i / 36
            u = (0.0, math.cos(a), math.sin(a))
            r, h = 0.61, dm0 + 0.20
            parts.box(f"huygens_vane_{i + 1}", (0.006, 0.08, 0.07),
                      location=(hc[0] - h, hc[1] + r * u[1], hc[2] + r * u[2]), direction=u, roll_deg=20,
                      material="foil_silver")

    # Back cover (Fig 2.2-5, facts.huygens_back_cover): 20 mm shell, estimated.
    cover = [(0.895, 0.0), (0.895, 0.1515), (0.85, 0.1965), (0.6249, 0.488), (0.3433, 0.578),
             (0.1609, 0.61), (0.0, 0.61)]
    with parts.assembly("huygens_back_cover", within="huygens"):
        parts.lathe("huygens_back_cover", cover + [(0.0, 0.59)] + [(max(r - 0.02, 0), h - 0.02 if h > 0 else h)
                                                                    for r, h in reversed(cover[:-1])],
                    location=hc, direction=out, segments=48, material="blanket_amber")
    # LGA2 below Huygens, pointing -X (our +x) (facts.lga2): 6.4 cm across and 33.5 cm long
    # (documents), on the axis and with its tip where NASA's assembly model has it (ref lga2);
    # its mount plate and stub support copied from that model.
    lg = ref["lga2"]
    L = d["lga2_length"]
    with parts.assembly("lga2"):
        parts.cylinder("lga2", radius=d["lga2_diameter"] / 2, length=L, location=(lg["tip_x"] - L, 0.0, lg["axis_z"]),
                       direction=(1, 0, 0), segments=16, material="white_paint")
        parts.mesh_file("lga2_mount", "refs/cassini/meshes/lga2_mount.json", material="white_paint")
        parts.mesh_file("lga2_boom", "refs/cassini/meshes/lga2_boom.json", material="white_paint")

    # Remote sensing pallet on our -x (spacecraft +X): the pallet under its gold blanket from NASA
    # model A, the instruments on it (cameras, spectrometers and their radiators) from NASA's
    # assembly model, one mesh per finish.
    with parts.assembly("rsp"):
        parts.mesh_file("rsp", "refs/cassini/meshes/rsp_blanket.json", material="blanket_amber")
        for name, mat in (("black", "blanket_black"), ("silver", "foil_silver"), ("white", "white_paint"),
                          ("gold", "blanket_amber")):
            parts.mesh_file(f"rsp_{name}", f"refs/cassini/meshes/rsp_{name}.json", material=mat)
    # Fields and particles pallet (our +x side, toward -y) under its black blanket, with the
    # instruments on it: all from NASA model A, the as-flown look (the assembly model's pallet is
    # bare and differs in places), one mesh per finish.
    with parts.assembly("fpp"):
        parts.mesh_file("fpp", "refs/cassini/meshes/fpp_black_krinkle.json", material="blanket_black")
        for name, mat in (("plastic_dark", "black"), ("plastic_white", "white_paint"), ("aluminum", "foil_silver")):
            parts.mesh_file(f"fpp_{name}", f"refs/cassini/meshes/fpp_{name}.json", material=mat)

    # Magnetometer boom along +y (facts.mag_sensors): a three-longeron mast ("coiled longeron
    # mast") 0.275 m across, apex down, from the canister to the tip fitting, placed as NASA's
    # assembly model has it (ref mag_boom). The sensors and their fittings are copied from that
    # model: flux-gate 5.814 m and helium magnetometer 11.015 m from the spacecraft centre
    # (checked: mag_fgm_distance, mag_vhm_distance). The canister under its blanket from model A.
    mb = ref["mag_boom"]
    parts.mesh_file("mag_canister", "refs/cassini/meshes/mag_canister.json", material="blanket_amber")
    with parts.assembly("mag_boom"):
        for name, (y0, y1) in (("mag_boom", (mb["root_y"], mb["gap_y"][0])), ("mag_boom_2", (mb["gap_y"][1], mb["tip_y"]))):
            parts.boom(name, length=y1 - y0, width=mb["width"], location=(0, y0, mb["axis_z"]),
                       direction=(0, 1, 0), material="dark_metal")
        for name in ("mag_fgm_bracket", "mag_fgm", "mag_fgm_mount", "mag_tip", "mag_vhm"):
            parts.mesh_file(name, f"refs/cassini/meshes/{name}.json", material="foil_silver")

    # RPWS: three 10 m monopoles, 2.86 cm across (facts.rpws_layout), pointing as Table III of
    # Gurnett et al. 2004 gives them (facts.rpws_angles: polar angle from the spacecraft +Z,
    # azimuth from +X), turned into our frame (the spacecraft frame turned 180 deg about Y).
    # Roots from model A, each on a short mount back to the boom canister (estimated: model A's
    # roots sit just off it).
    for i, (r0, ant) in enumerate(zip(ref["rpws_roots"], ("Ev", "Eu", "Ew"))):
        th, ph = (math.radians(a) for a in spec["facts"]["rpws_angles"]["value"][ant])
        v = (-math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), -math.cos(th))
        parts.strut(f"rpws_mount_{i + 1}", P(r0), P(ref["mag_canister"]["centre"]), radius=0.03, material="blanket_amber")
        parts.cylinder(f"rpws_{i + 1}", radius=d["rpws_antenna_diameter"] / 2, length=d["rpws_antenna_length"],
                       location=P(r0), direction=v, segments=6, material="dark_metal")

    # Thermal blankets: every part in the gold or black blanket finish gets crinkled foil (the
    # spec's sampled colours; crease sizes estimated by eye from pia04603, no document gives
    # them), mapped by box projection since most blankets are copied meshes, not lathes.
    sm = spec["materials"]
    foils = {}
    for name in ("blanket_amber", "blanket_black"):
        fb, fn = tiling.crinkled_foil("cassini", f"{name}_foil", sm[name]["hex"], facet=0.06, tilt_deg=9,
                                      wrinkle=0.25, wrinkle_deg=8, spread=0.06, stretch=1.5,
                                      repeat=(FOIL_TILE, FOIL_TILE), px_per_m=700)
        foils[name] = materials.image(f"{name}_crinkled", fb, normal=fn, metallic=sm[name]["metallic"],
                                      roughness=sm[name]["roughness"])
    for obj in list(parts.collection().objects):
        if obj.type != "MESH" or not obj.data.materials:
            continue
        mats = obj.data.materials
        hit = [i for i, m in enumerate(mats) if m and m.name in foils]
        if not hit:
            continue
        for i in hit:
            mats[i] = foils[mats[i].name]
        tiling.box_uv(obj, FOIL_TILE)


FOIL_TILE = 0.6  # metres per foil tile
