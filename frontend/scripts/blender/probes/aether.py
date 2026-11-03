# Altair Aether: a lunar communications relay on its mass-driver sled. Every number comes from
# specs/aether.json (sourced, or a design value said to be one).
# Frame: x along the track (the direction of travel and the craft's axis, so the launch load runs
# down it), z up, y left. The craft's separation plane is at x = 0; the sled pushes from behind.
import math
from lib import parts

X = (1, 0, 0)


def build(spec):
    d = {k: v["value"] for k, v in {**spec["facts"], **spec["dimensions"]}.items()}
    R = d["hex_corner_radius"]
    flat = R * math.cos(math.pi / 6)                 # centre to the middle of a side
    hexa = dict(segments=6, smooth=False, direction=X, roll_deg=30.0)  # a flat side facing down (-z)
    rb, ro = d["sep_ring_bolt_circle"] / 2, d["sep_ring_diameter"] / 2
    ri = rb - (ro - rb)                              # inner edge as far inside the bolts as the outer is out
    hu, hl = d["sep_ring_upper_height"], d["sep_ring_lower_height"]
    xc, t = d["cone_length"], d["deck_thickness"]   # the cone runs from the ring to the lower deck at xc
    xb = xc + d["body_length"]

    with parts.assembly("structure", core=True):
        # The separation ring's craft half, then a cone carrying the load out to the lower deck.
        parts.lathe("sep_ring_upper", [(ri, 0), (ro, 0), (ro, hu), (ri, hu)], closed=True, segments=48,
                    direction=X, material="foil_silver")
        r_top = flat - 0.04
        parts.lathe("cone", [(rb - 0.004, hu), (rb, hu), (r_top, xc), (r_top - 0.004, xc)], closed=True,
                    segments=48, direction=X, material="dark_metal")
        parts.lathe("deck_lower", [(0, xc), (R, xc), (R, xc + t), (0, xc + t)], material="white_paint", **hexa)
        parts.lathe("deck_upper", [(0, xb - t), (R, xb - t), (R, xb), (0, xb)], material="white_paint", **hexa)
        parts.lathe("side_panels", [(R - 0.004, xc + t), (R, xc + t), (R, xb - t), (R - 0.004, xb - t)],
                    closed=True, material="foil_gold", **hexa)

    with parts.assembly("tank"):
        # Northrop Grumman 80583-1 (104 L, 83 kg hydrazine), standing on the lower deck.
        rt = d["tank_diameter"] / 2
        x0 = xc + t + rt
        prof = [(0.0, x0 - rt)] + [(rt * math.sin(math.pi * k / 24), x0 - rt * math.cos(math.pi * k / 24))
                                    for k in range(1, 24)] + [(0.0, x0 + rt)]
        parts.lathe("tank", prof, segments=48, direction=X, material="foil_silver")

    with parts.assembly("main_thruster"):
        # ArianeGroup 20 N: hung under the lower deck, firing back through the separation ring.
        L, rn = d["main_thruster_length"], d["main_thruster_nozzle"] / 2
        parts.lathe("main_thruster", [(0.0, 0.0), (0.016, 0.0), (0.016, 0.045), (0.011, 0.05), (0.011, 0.12),
                                      (0.007, 0.13), (rn, L), (rn - 0.001, L), (0.006, 0.13), (0.0, 0.125)],
                    segments=24, location=(xc, 0, 0), direction=(-1, 0, 0), material="dark_metal")

    # The sled: a pusher bulkhead bolted to the ring's lower half takes the launch load; the craft's
    # flat underside rests on the base (its weight in lunar gravity); it runs on four shoes, driven through the armature plate beneath.
    gauge, base_z = d["rail_gauge"], -flat
    with parts.assembly("sled"):
        parts.lathe("sep_ring_lower", [(ri, -hl), (ro, -hl), (ro, 0), (ri, 0)], closed=True, segments=48,
                    direction=X, material="foil_silver")
        xp = -hl - 0.02
        parts.box("pusher", (0.04, 2 * R, 2 * flat + 0.05), location=(xp, 0, 0.025), material="dark_metal")
        x_end = xb
        L_base = x_end - (xp - 0.02)
        parts.box("sled_base", (L_base, gauge + 0.1, 0.05), location=((x_end + xp - 0.02) / 2, 0, base_z - 0.025),
                  material="dark_metal")
        for k, (sx, sy) in enumerate([(0.0, 1), (0.0, -1), (x_end - 0.1, 1), (x_end - 0.1, -1)]):
            parts.box(f"shoe{k}", (0.14, 0.1, 0.05), location=(sx, sy * gauge / 2, base_z - 0.075), material="dark_metal")
        parts.box("armature", (L_base - 0.2, 0.3, 0.03), location=((x_end + xp - 0.02) / 2, 0, base_z - 0.065),
                  material="foil_silver")

    with parts.assembly("track"):
        for k, sy in enumerate((1, -1)):
            parts.box(f"rail{k}", (4.0, 0.08, 0.12), location=(0.5, sy * gauge / 2, base_z - 0.16), material="dark_metal")
        parts.box("stator", (4.0, 0.3, 0.04), location=(0.5, 0, base_z - 0.1), material="dark_metal")
