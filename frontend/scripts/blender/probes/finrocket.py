# Fin-steered model rocket: our own design on real parts. Every number comes from
# specs/finrocket.json (tube, motor mount, motor and servo sizes sourced; nose and fins design values).
# Frame: z up along the rocket, the body tube's base at z = 0. Fin i stands on the radial line at
# 90° × i from +x (fin 0 on +x), as the flight sim on /circuits/fly numbers them.
import math
from lib import parts

def build(spec):
    # Measured sizes (dimensions) and the rest (facts: inside diameters, fin shape, servo size).
    d = {k: v["value"] for k, v in {**spec["facts"], **spec["dimensions"]}.items()}
    ro, ri = d["body_od"] / 2, d["body_id"] / 2
    lb, ln = d["body_length"], d["nose_length"]

    with parts.assembly("airframe", core=True):
        parts.lathe("body_tube", [(ri, 0), (ro, 0), (ro, lb), (ri, lb)], closed=True, segments=64)
        # Tangent ogive: an arc of radius rho through the tip, tangent to the tube at its base.
        rho = (ro * ro + ln * ln) / (2 * ro)
        prof = [(0.0, lb), (ro, lb)]
        for k in range(1, 24):
            x = ln * k / 24  # from the base toward the tip
            prof.append((math.sqrt(rho * rho - x * x) + ro - rho, lb + x))
        prof.append((0.0, lb + ln))
        parts.lathe("nose", prof, segments=64, material="black")

    mo, mi, ml = d["mount_od"] / 2, d["mount_id"] / 2, d["mount_length"]
    with parts.assembly("motor_mount"):
        parts.lathe("motor_mount", [(mi, 0), (mo, 0), (mo, ml), (mi, ml)], closed=True, segments=48,
                    material="dark_metal")
        for name, z in (("ring_aft", 0.002), ("ring_fwd", ml - 0.005)):  # 3 mm rings: design
            parts.lathe(name, [(mo, z), (ri, z), (ri, z + 0.003), (mo, z + 0.003)], closed=True,
                        segments=48, material="dark_metal")
    with parts.assembly("motor"):
        parts.cylinder("motor", d["motor_diameter"] / 2, d["motor_length"], location=(0, 0, 0),
                       segments=32, material="white_paint")

    # Fins: all-moving trapezoids, each on a radial shaft at the quarter of its mean aerodynamic
    # chord (or_techdoc: the fin's centre of pressure), so the servo holds little load.
    cr, ct, s, sw = d["fin_root_chord"], d["fin_tip_chord"], d["fin_span"], d["fin_sweep"]
    n, area = 200, (cr + ct) / 2 * s
    ys = [(k + 0.5) * s / n for k in range(n)]
    chord = lambda y: cr + (ct - cr) * y / s
    mac = sum(chord(y) ** 2 for y in ys) * (s / n) / area
    xle = sum(sw * y / s * chord(y) for y in ys) * (s / n) / area
    z_le = d["fin_root_te_height"] + cr          # root leading edge
    z_piv = z_le - (xle + 0.25 * mac)
    gap = 0.001                                  # fin root clear of the tube: design
    sx, sy, sz = d["servo_length"], d["servo_width"], d["servo_height"]  # along z, across, to the shaft
    z_servo = ml + 0.008                         # servos stand just forward of the mount: design
    for i in range(4):
        a = i * math.pi / 2
        r_hat = (math.cos(a), math.sin(a), 0.0)
        t_hat = (-math.sin(a), math.cos(a), 0.0)  # z × radial
        R = lambda r, z, r_hat=r_hat: (r * r_hat[0], r * r_hat[1], z)
        with parts.assembly(f"fin{i}"):
            fin = parts.surface(f"fin{i}", R(ro + gap, z_le), cr, R(ro + gap + s, z_le - sw), ct,
                                d["fin_thickness"] / cr, kind="lens", chord_dir=(0, 0, -1), material="black")
            shaft = parts.tube(f"fin{i}_shaft", [R(ri - 0.006, z_piv), R(ro + gap + 0.004, z_piv)], 0.001,
                               segments=8, material="dark_metal")
            horn = parts.box(f"fin{i}_horn", (0.0015, 0.008, 0.003), location=R(ri - 0.005, z_piv),
                             direction=(0, 0, 1), roll_deg=math.degrees(a), material="dark_metal")
            parts.hinge(f"fin{i}_j", [fin, shaft, horn], R(ri - 0.006, z_piv), R(ro + gap + s, z_piv),
                        sample=R(ro + gap, z_le - cr), want=tuple(-c for c in t_hat))
        with parts.assembly(f"servo{i}"):
            # Lying along the axis between the mount's front and the board, shaft pointing outward.
            r_c = ri - sz / 2 - 0.001
            parts.box(f"servo{i}", (sy, sx, sz), location=R(r_c, z_servo + sx / 2),
                      direction=r_hat, roll_deg=0.0, material="dark_metal")
            horn_pt = R(ri - 0.004, z_servo + 0.004)
            parts.tube(f"pushrod{i}", [horn_pt, R(ri - 0.004, z_piv), R(ri - 0.005, z_piv)], 0.0005,
                       segments=6, material="foil_silver")
