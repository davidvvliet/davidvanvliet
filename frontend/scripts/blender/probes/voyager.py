# Voyager. Built in the frame of NASA's reference model (refs/voyager/reference-sheet.png),
# so our sheet and the reference sheet overlay: z up with the dish on top, science boom
# toward +y, magnetometer and RTG booms toward -y. Metres. Checked sizes come from
# specs/voyager.json `dimensions`; positions and angles no document gives come from its
# `from_reference_model` (each with how it was measured).
import math, os
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

    # Upper ring between bus and dish (reference model), on a central post from the bus top
    # (post radius estimated from the reference close-up).
    ring = ref["upper_ring"]
    parts.cylinder("hga_mount", radius=0.35, length=ring["z"][0] - top, location=(0, 0, top), segments=20,
                   material="dark_metal")
    parts.prism("upper_ring", sides=20, radius=ring["radius"], height=ring["z"][1] - ring["z"][0],
                location=(0, 0, ring["z"][0]), material="black")

    # High-gain antenna, vertex at the reference model's height.
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

    # Strut frame under the bus down to an adapter ring (depth estimated, spec under_bus_depth).
    low = bottom - ref["under_bus_depth"]
    parts.cylinder("adapter_ring", radius=0.25, length=0.06, location=(0, 0, low), segments=20,
                   material="dark_metal")
    for i in range(4):
        a = math.radians(45 + 90 * i)
        c, sn = math.cos(a), math.sin(a)
        parts.strut(f"under_strut_{i + 1}", (0.7 * c, 0.7 * sn, bottom), (0.24 * c, 0.24 * sn, low + 0.06),
                    radius=0.025)

    # Golden record: its aluminium cover (what shows on the bus; facts.record_cover), flat on
    # the bus face where the reference model's texture shows it. Size from the Smithsonian's
    # duplicate cover; engravings as a colour + normal map made from the fitted line drawing
    # (from_reference_model.record_texture). Checked by spec `mounts`.
    rc = ref["record_centre"]
    a = math.radians(rc["azimuth_deg"])
    n = (math.cos(a), math.sin(a), 0.0)
    hub = ref["record_hub"]
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
    # Scan platform in three layers inside the reference model's box (spec scan_platform_box):
    # instruments full width below, a narrower block above, a post on top.
    b = ref["scan_platform_box"]
    (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for name, (w, l), za, zb in (("scan_lower", (x1 - x0, y1 - y0), z0, 0.44),
                                 ("scan_upper", (0.49, 0.46), 0.44, 0.91),
                                 ("scan_post", (0.15, 0.15), 0.91, z1)):
        parts.box(name, (w, l, zb - za), location=(cx, cy, (za + zb) / 2), material="black")

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
