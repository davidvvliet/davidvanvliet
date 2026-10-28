# Voyager. Built in the frame of NASA's reference model (refs/voyager/reference-sheet.png),
# so our sheet and the reference sheet overlay: z up with the dish on top, science boom
# toward +y, magnetometer and RTG booms toward -y. Metres. Checked sizes come from
# specs/voyager.json `dimensions`; positions and angles no document gives come from its
# `from_reference_model` (each with how it was measured).
import math, os
from mathutils import Vector
from lib import materials, parts, textures

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _along(start, direction, s):
    return tuple(start[i] + direction[i] * s for i in range(3))

def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)

def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    ref = {k: v["value"] for k, v in spec["from_reference_model"].items()}

    # Bus: decagon (NSSDCA size), centred on the reference model's bus height band, with a
    # flat facing +x like the reference model (prism roll 0 puts corners at +-18 deg).
    bus_h, bus_r = d["bus_height"], d["bus_across_corners"] / 2
    flat_r = bus_r * math.cos(math.radians(18))
    bottom = sum(ref["bus_z"]) / 2 - bus_h / 2
    top = bottom + bus_h
    parts.prism("bus", sides=10, radius=bus_r, height=bus_h, location=(0, 0, bottom),
                roll_deg=ref["bus_flat_azimuth_deg"], material="black")

    # Bus details from the reference model (spec bus_details): the domed blanket on the bus top,
    # the plate under it, two grille units on the top, boxes under the record and opposite it.
    bd = ref["bus_details"]
    parts.lathe("bus_blanket", [tuple(p) for p in bd["top_blanket"]], segments=40, material="black")
    bp = bd["bottom_plate"]
    parts.prism("bus_bottom_plate", sides=10, radius=bp["radius"], height=bp["z"][1] - bp["z"][0],
                location=(0, 0, bp["z"][0]), roll_deg=ref["bus_flat_azimuth_deg"], material="black")
    ax = bd["top_boxes_axis"]
    yaw = math.degrees(math.atan2(ax[1], ax[0]))
    for i, unit in enumerate(bd["top_boxes"]):
        for part in ("grille", "body"):
            b = unit[part]
            parts.box(f"top_{part}_{i + 1}", tuple(b["size"]), location=tuple(b["centre"]), roll_deg=yaw,
                      material="black")
    for i, b in enumerate(bd["record_boxes"]):
        parts.box(f"record_box_{i + 1}", tuple(b["size"]), location=tuple(b["centre"]), material="black")

    # Upper ring between bus and dish (reference model), on two pairs of struts from the bus top.
    ring = ref["upper_ring"]
    for i, (a0, a1) in enumerate(bd["ring_struts"]):
        parts.strut(f"ring_strut_{i + 1}", a0, a1, radius=bd["ring_strut_radius"])
    parts.prism("upper_ring", sides=20, radius=ring["radius"], height=ring["z"][1] - ring["z"][0],
                location=(0, 0, ring["z"][0]), material="black", cap_top=False)

    # High-gain antenna: the reference model's paraboloid (vertex height and depth fitted to it).
    vertex = ref["hga_vertex_z"]
    parts.dish("hga", diameter=d["hga_diameter"], depth=ref["hga_depth"], location=(0, 0, vertex))
    # Feed: four legs from the dish surface up to a platform, a gold feed cylinder on top,
    # and the horn at the dish centre (sizes from the reference model, spec feed_*).
    fp, fh = ref["feed_platform"], ref["feed_horn"]
    R = d["hga_diameter"] / 2
    plat_r = fp["diameter"] / 2
    parts.cylinder("feed_platform", radius=plat_r, length=0.05, location=(0, 0, fp["z"] - 0.05),
                   segments=16, material="dark_metal")
    parts.cylinder("feed", radius=0.08, length=fp["top_z"] - fp["z"], location=(0, 0, fp["z"]),
                   segments=16, material="foil_gold")
    leg_r = 1.0  # where the legs meet the dish (estimated from the reference close-up)
    leg_z = vertex + ref["hga_depth"] * (leg_r / R) ** 2
    for i in range(4):
        a = math.radians(45 + 90 * i)
        c, sn = math.cos(a), math.sin(a)
        parts.strut(f"feed_leg_{i + 1}", (leg_r * c, leg_r * sn, leg_z),
                    (plat_r * 0.9 * c, plat_r * 0.9 * sn, fp["z"] - 0.05), radius=0.02)
    parts.cylinder("feed_horn", radius=fh["diameter"] / 2, length=fh["top_z"] - vertex,
                   location=(0, 0, vertex), segments=16, material="foil_silver")

    # Under the bus (spec bus_details): eight legs from four corners to eight feet, and a flat
    # panel on the +y side carried by two struts.
    for i, (a0, a1) in enumerate(bd["under_legs"]):
        parts.strut(f"under_leg_{i + 1}", a0, a1, radius=bd["under_leg_radius"])
    up_ = bd["under_panel"]
    t0, t1 = Vector(up_["edge_top"][0]), Vector(up_["edge_top"][1])
    b0 = Vector(up_["edge_bottom"][0])
    across, down = t1 - t0, b0 - t0
    normal = down.cross(across).normalized()
    if normal.z < 0:
        normal = -normal
    centre = (t0 + t1) / 2 + down / 2 - normal * up_["thickness"] / 2
    parts.plate("under_panel", across.length, down.length, up_["thickness"], location=tuple(centre),
                direction=tuple(normal), up=tuple(-down), material="black")
    for i, (a0, a1) in enumerate(bd["under_panel_struts"]):
        parts.strut(f"under_panel_strut_{i + 1}", a0, a1, radius=bd["under_panel_strut_radius"])

    # Golden record: its aluminium cover (what shows on the bus; facts.record_cover), flat on
    # the bus face where the reference model's texture shows it. Size from the Smithsonian's
    # duplicate cover; engravings as a colour + normal map made from the fitted line drawing
    # (from_reference_model.record_texture). Checked by spec `mounts`.
    rc = ref["record_centre"]
    a = math.radians(rc["azimuth_deg"])
    n = (math.cos(a), math.sin(a), 0.0)
    hub = ref["record_hub"]  # its hole goes all the way through the record and cover
    base, normal = textures.engraved("golden_record", os.path.join(HARNESS, ref["record_texture"]["lines"]),
                                     os.path.join(HARNESS, "out", "voyager", "textures"), base=tuple(ref["record_gold"]))
    parts.disc("golden_record", radius=d["record_diameter"] / 2, thickness=d["record_depth"] - hub["height"],
               location=(flat_r * n[0], flat_r * n[1], rc["z"]), direction=n, roll_deg=ref["record_roll_deg"],
               hub=hub, material=materials.image("golden_record_cover", base, normal, metallic=1.0, roughness=ref["record_roughness"]))

    # Magnetometer boom: a support truss from the bus out to the boom interface, then the
    # 13 m Astromast at the reference model's elevation. Lattice widths are estimated from
    # the reference sheet.
    # The support truss is collinear with the boom: the reference model's boom line runs
    # straight back into the bus, so the truss starts where that line meets the bus side.
    iface = tuple(ref["mag_boom_interface"])
    e = math.radians(ref["mag_boom_elevation_deg"])
    mag_dir = (0.0, -math.cos(e), math.sin(e))
    back = (iface[1] - (-flat_r * 0.8)) / mag_dir[1]   # step back along the line to just inside the bus
    truss_root = _along(iface, mag_dir, -back)
    truss_vec = tuple(iface[i] - truss_root[i] for i in range(3))
    truss_len = math.sqrt(sum(x * x for x in truss_vec))
    parts.boom("mag_support", length=truss_len, width=0.3, location=truss_root, direction=truss_vec,
               material="dark_metal")
    L = d["mag_boom_length"]
    parts.boom("mag_boom", length=L, width=0.25, location=iface, direction=mag_dir, material="foil_silver")
    # Canister the Astromast deploys from, around the boom root (estimated, spec mag_canister).
    can = ref["mag_canister"]
    parts.cylinder("mag_canister", radius=can["diameter"] / 2, length=can["length"],
                   location=_along(iface, mag_dir, -can["length"] / 2), direction=mag_dir, segments=20,
                   material="foil_silver")
    # Low-field magnetometers at the tip and at 0.57 of the length; the two high-field ones
    # ~1 m apart on the support truss (facts.mag_sensor_positions). Sensor sizes estimated.
    for name, f in (("lfm_outer", 1.0), ("lfm_inner", 0.57)):
        parts.cylinder(name, radius=ref["lfm_sensor"]["diameter"] / 2, length=0.2,
                       location=_along(iface, mag_dir, L * f - 0.1), direction=mag_dir, segments=16,
                       material="black")  # drums, diameter from the reference model
    tu = _unit(truss_vec)
    for name, s in (("hfm_inner", truss_len * 0.3), ("hfm_outer", truss_len * 0.3 + 1.0)):
        if s < truss_len:
            parts.box(name, (0.36, 0.36, 0.12), location=_along(truss_root, tu, s), direction=tu,
                      material="black")

    # RTGs: three units in tandem between the reference model's inner and outer ends,
    # drooping by its measured slope; a strut boom carries them from the bus underside.
    # Body diameter 40.6 cm (NSSDCA), fin span from the reference model.
    droop = math.radians(ref["rtg_stack_droop_deg"])
    rtg_dir = (0.0, -math.cos(droop), -math.sin(droop))
    y_in = ref["rtg_stack_inner_y"]
    z_in = ref["rtg_stack_centre_z_at_inner"] + math.tan(droop) * (y_in - (-2.6))
    inner = (0.0, y_in, z_in)
    unit, n = d["rtg_length"], 3
    space = 0.0  # mounted in tandem: units bolt end to end (NSSDCA "mounted in tandem")
    arm_root = (0.0, -flat_r, bottom + 0.1)
    arm_vec = tuple(inner[i] - arm_root[i] for i in range(3))
    parts.boom("rtg_boom", length=math.sqrt(sum(x * x for x in arm_vec)), width=0.2, location=arm_root,
               direction=arm_vec, material="dark_metal")
    for i in range(n):
        parts.rtg(f"rtg_{i + 1}", length=unit, radius=d["rtg_diameter"] / 2, fin_span=ref["rtg_fin_span"],
                  fins=6, location=_along(inner, rtg_dir, i * (unit + space)), direction=rtg_dir,
                  separate_fins=True)

    # Science boom toward +y from the bus face, scan platform at its end (a placeholder block
    # this pass, reaching the reference model's outer extent of ~4.2 m).
    sci_z = ref["science_boom_z"]
    parts.boom("science_boom", length=d["science_boom_length"], width=0.3, location=(0, flat_r, sci_z),
               direction=(0, 1, 0), material="dark_metal")
    end = flat_r + d["science_boom_length"]
    # Scan platform: the reference model's pieces (spec scan_platform), wrapped boxes and
    # the post, tube, camera barrels and telescope as cylinders.
    sp = ref["scan_platform"]
    for name, (lo, hi) in sp["boxes"].items():
        parts.box(name, tuple(h - l for l, h in zip(lo, hi)), location=tuple((l + h) / 2 for l, h in zip(lo, hi)),
                  material="black")
    for name, c in sp["cylinders"].items():
        a0, a1 = Vector(c["from"]), Vector(c["to"])
        open_tube = c.get("open", False)
        parts.cylinder(name, c["radius"], (a1 - a0).length, location=tuple(a0), direction=tuple(a1 - a0),
                       segments=24, material="black", caps=not open_tube)
        if open_tube:   # the lens at the back of a sunshade
            parts.cylinder(name + "_lens", c["radius"] * 0.95, 0.01, location=tuple(a0), direction=tuple(a1 - a0),
                           segments=24, material="black")
    for name, c in sp["dishes"].items():
        parts.dish(name, diameter=c["diameter"], depth=c["depth"], location=tuple(c["vertex"]),
                   direction=tuple(c["direction"]), thickness=0.01, material="black")

    # Plasma wave / radio astronomy whips: two 10 m rods at 90 degrees (facts.whip_angle_deg),
    # symmetric about the reference model's mean whip direction, from its root point.
    # Rod diameter ~0.5 in (Scarf & Gurnett, OCR).
    mean = (0.0, -0.596, -0.803)          # normalised mean of the reference model's two whips
    half = math.radians(90 / 2)
    root = (0.0, -1.09, 0.19)             # reference model whip root
    # Their base housing on the magnetometer support truss (spec whip_base_box).
    wb = ref["whip_base_box"]
    parts.box("whip_base", tuple(wb["size"]), location=tuple(wb["centre"]), material="dark_metal")
    for name, sx in (("whip_a", 1), ("whip_b", -1)):
        v = (sx * math.sin(half), mean[1] * math.cos(half), mean[2] * math.cos(half))
        parts.cylinder(name, radius=0.0064, length=d["whip_length"], location=root, direction=v,
                       segments=6, material="dark_metal")
