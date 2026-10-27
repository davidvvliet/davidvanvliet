# Voyager. Built in the frame of NASA's reference model (refs/voyager/reference-sheet.png),
# so our sheet and the reference sheet overlay: z up with the dish on top, science boom
# toward +y, magnetometer and RTG booms toward -y. Metres. Checked sizes come from
# specs/voyager.json `dimensions`; positions and angles no document gives come from its
# `from_reference_model` (each with how it was measured).
import math
from lib import parts

def _along(start, direction, s):
    return tuple(start[i] + direction[i] * s for i in range(3))

def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)

def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    ref = {k: v["value"] for k, v in spec["from_reference_model"].items()}

    # Bus: decagon (NSSDCA size), top at the reference model's bus top.
    bus_h, bus_r = d["bus_height"], d["bus_across_corners"] / 2
    flat_r = bus_r * math.cos(math.radians(18))
    top = ref["frame_bus_top_z"]
    bottom = top - bus_h
    parts.prism("bus", sides=10, radius=bus_r, height=bus_h, location=(0, 0, bottom), roll_deg=18,
                material="black")

    # High-gain antenna, vertex above the bus top by the reference model's gap.
    gap = ref["hga_vertex_above_bus"]
    parts.dish("hga", diameter=d["hga_diameter"], depth=ref["hga_depth"], location=(0, 0, top + gap))
    parts.cylinder("hga_mount", radius=0.35, length=gap, location=(0, 0, top), segments=20,
                   material="dark_metal")

    # Magnetometer boom: a support truss from the bus out to the boom interface, then the
    # 13 m Astromast at the reference model's elevation. Lattice widths are estimated from
    # the reference sheet.
    iface = tuple(ref["mag_boom_interface"])
    truss_root = (0, -flat_r, top - 0.1)
    truss_vec = tuple(iface[i] - truss_root[i] for i in range(3))
    truss_len = math.sqrt(sum(x * x for x in truss_vec))
    parts.boom("mag_support", length=truss_len, width=0.3, location=truss_root, direction=truss_vec,
               material="dark_metal")
    e = math.radians(ref["mag_boom_elevation_deg"])
    mag_dir = (0.0, -math.cos(e), math.sin(e))
    L = d["mag_boom_length"]
    parts.boom("mag_boom", length=L, width=0.25, location=iface, direction=mag_dir, material="foil_silver")
    # Low-field magnetometers at the tip and at 0.57 of the length; the two high-field ones
    # ~1 m apart on the support truss (facts.mag_sensor_positions). Sensor sizes estimated.
    for name, f in (("lfm_outer", 1.0), ("lfm_inner", 0.57)):
        parts.box(name, (0.18, 0.18, 0.18), location=_along(iface, mag_dir, L * f), material="black")
    tu = _unit(truss_vec)
    for name, s in (("hfm_inner", truss_len * 0.3), ("hfm_outer", truss_len * 0.3 + 1.0)):
        if s < truss_len:
            parts.box(name, (0.12, 0.12, 0.12), location=_along(truss_root, tu, s), material="black")

    # RTGs: three units in tandem between the reference model's inner and outer ends,
    # drooping by its measured slope; a strut boom carries them from the bus underside.
    # Body diameter 40.6 cm (NSSDCA), fin span from the reference model.
    droop = math.radians(ref["rtg_stack_droop_deg"])
    rtg_dir = (0.0, -math.cos(droop), -math.sin(droop))
    y_in, y_out = ref["rtg_stack_inner_y"], ref["rtg_stack_outer_y"]
    z_in = ref["rtg_stack_centre_z_at_inner"] + math.tan(droop) * (y_in - (-2.6))
    inner = (0.0, y_in, z_in)
    run = (y_in - y_out) / math.cos(droop)
    unit, n = d["rtg_length"], 3
    space = (run - n * unit) / (n - 1)
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
    sci_z = bottom + bus_h * 0.6
    parts.boom("science_boom", length=d["science_boom_length"], width=0.3, location=(0, flat_r, sci_z),
               direction=(0, 1, 0), material="dark_metal")
    end = flat_r + d["science_boom_length"]
    parts.box("scan_platform", (0.6, 4.2 - end, 0.55), location=(0, (end + 4.2) / 2, sci_z + 0.1),
              material="black")

    # Plasma wave / radio astronomy whips: two 10 m rods at 90 degrees (facts.whip_angle_deg),
    # symmetric about the reference model's mean whip direction, from its root point.
    # Rod diameter ~0.5 in (Scarf & Gurnett, OCR).
    mean = (0.0, -0.596, -0.803)          # normalised mean of the reference model's two whips
    half = math.radians(90 / 2)
    root = (0.0, -1.09, 0.19)             # reference model whip root
    for name, sx in (("whip_a", 1), ("whip_b", -1)):
        v = (sx * math.sin(half), mean[1] * math.cos(half), mean[2] * math.cos(half))
        parts.cylinder(name, radius=0.0064, length=d["whip_length"], location=root, direction=v,
                       segments=6, material="dark_metal")
