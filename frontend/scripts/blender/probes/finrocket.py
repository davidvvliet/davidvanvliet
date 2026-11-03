# Fin-steered model rocket: our own design on real parts. Every number comes from
# specs/finrocket.json (tube, motor mount, motor and servo sizes sourced; nose and fins design values).
# Frame: z up along the rocket, the body tube's base at z = 0. Fin i stands on the radial line at
# 90° × i from +x (fin 0 on +x), as the flight sim on /circuits/fly numbers them.
import math, os
from lib import materials, parts, textures

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build(spec):
    # Measured sizes (dimensions) and the rest (facts: inside diameters, fin shape, servo size).
    d = {k: v["value"] for k, v in {**spec["facts"], **spec["dimensions"]}.items()}
    ro, ri = d["body_od"] / 2, d["body_id"] / 2
    lb, ln = d["body_length"], d["nose_length"]

    with parts.assembly("airframe", core=True):
        tube = parts.lathe("body_tube", [(ri, 0), (ro, 0), (ro, lb), (ri, lb)], closed=True, segments=64)
        # Tangent ogive with a rounded tip: an arc of radius rho tangent to the tube at its base, and a
        # sphere of radius rn on the axis tangent to the arc. rho is found so the nose keeps its length.
        rn = d["nose_tip_radius"]
        def blunt(rho):
            xc = math.sqrt((rho - rn) ** 2 - (rho - ro) ** 2)  # sphere centre, from the base
            return xc, xc + rn
        lo, hi = ro, 50 * ln
        for _ in range(80):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if blunt(mid)[1] < ln else (lo, mid)
        rho = (lo + hi) / 2
        xc = blunt(rho)[0]
        # Tangent point: on the line from the arc's centre (x 0, r ro - rho) through the sphere's centre.
        k = rho / (rho - rn)
        xt, rt_ = xc * k, (ro - rho) + (0 - (ro - rho)) * k
        prof = [(0.0, lb), (ro, lb)]
        for j in range(1, 24):
            x = xt * j / 24
            prof.append((math.sqrt(rho * rho - x * x) + ro - rho, lb + x))
        th0 = math.atan2(rt_, xt - xc)                       # tangent point's angle on the sphere
        for j in range(0, 9):
            t = th0 * (1 - j / 8)
            prof.append((rn * math.sin(t), lb + xc + rn * math.cos(t)))
        parts.lathe("nose", prof, segments=64, material="black")

    # Roll pattern below the nose: the band split in quarters on the fin lines, two opposite ones
    # black, so a roll shows. Painted by geometry (decal shapes): sharp edges, no image.
    z1, z2 = lb - d["roll_band_from_top"] - d["roll_band_length"], lb - d["roll_band_from_top"]
    for q in (0, 2):
        a = (q + 0.5) * math.pi / 2                  # quarter centred between fin q and fin q + 1
        with parts.assembly(f"roll_quarter{q}"):
            parts.decal(f"roll_quarter{q}", tube, center=(ro * math.cos(a), ro * math.sin(a), (z1 + z2) / 2),
                        direction=(-math.cos(a), -math.sin(a), 0), up=(0, 0, 1),
                        width=ro * math.pi / 2, height=z2 - z1, material="black", shapes=[[0, 0, 1, 1]])

    # The motor tube stands out aft of the body (mount_overhang) for the screw-on retainer, as in the
    # kit's instructions: a threaded ring epoxied over the tube and a cap whose lip holds the motor's rim.
    mo, mi, ml = d["mount_od"] / 2, d["mount_id"] / 2, d["mount_length"]
    za = -d["mount_overhang"]                    # aft end of the motor tube and of the motor
    with parts.assembly("motor_mount"):
        parts.lathe("motor_mount", [(mi, za), (mo, za), (mo, za + ml), (mi, za + ml)], closed=True, segments=48,
                    material="dark_metal")
        for name, z in (("ring_aft", 0.002), ("ring_fwd", za + ml - 0.005)):  # 3 mm rings: design
            parts.lathe(name, [(mo, z), (ri, z), (ri, z + 0.003), (mo, z + 0.003)], closed=True,
                        segments=48, material="dark_metal")
    rt, lb_ = d["retainer_thread_od"] / 2, d["retainer_base_length"]
    rc, lc, lip, rl = d["retainer_cap_od"] / 2, d["retainer_cap_length"], d["retainer_lip"], d["retainer_lip_id"] / 2
    with parts.assembly("retainer"):
        parts.lathe("retainer_base", [(mo, za), (rt, za), (rt, za + lb_), (mo, za + lb_)], closed=True,
                    segments=48, material="retainer_grey")
        # The cap: sixteen flats outside (Estes' photo), the lip across the motor's rim at its aft end.
        parts.lathe("retainer_cap", [(rt, za - lip), (rc, za - lip), (rc, za - lip + lc), (rt, za - lip + lc)],
                    closed=True, segments=16, smooth=False, material="retainer_grey")
        parts.lathe("retainer_lip", [(rl, za - lip), (rt, za - lip), (rt, za), (rl, za)], closed=True,
                    segments=48, material="retainer_grey")
    # The motor: a paper casing, its clay nozzle set back from the aft end, a cone opening from the
    # throat to the exit, and the propellant's face above the throat.
    r_m, wall = d["motor_diameter"] / 2, d["motor_wall"]
    zn = za + d["nozzle_recess"]                 # nozzle's aft face
    ln_, re, rth = d["nozzle_length"], d["nozzle_exit_d"] / 2, d["nozzle_throat_d"] / 2
    with parts.assembly("motor"):
        parts.lathe("motor", [(r_m - wall, za), (r_m, za), (r_m, za + d["motor_length"]), (r_m - wall, za + d["motor_length"])],
                    closed=True, segments=48, material="kraft")
        parts.lathe("motor_nozzle", [(re, zn), (r_m - wall, zn), (r_m - wall, zn + ln_), (rth, zn + ln_), (rth, zn + 0.6 * ln_)],
                    closed=True, segments=48, material="nozzle_clay")
        parts.lathe("motor_grain", [(0.0, zn + ln_), (rth + 0.0005, zn + ln_), (rth + 0.0005, zn + ln_ + 0.001), (0.0, zn + ln_ + 0.001)],
                    segments=24, material="black")

    # Launch lugs: between the fins (45° from fin 0 and fin 3), each even with the aft end of a body tube.
    lr, ll, lw = d["lug_id"] / 2, d["lug_length"], d["lug_wall"]
    with parts.assembly("lugs"):
        a = -math.pi / 4
        rr = ro + lr + lw - 0.0002               # resting on the tube
        for name, z in (("lug_aft", 0.0), ("lug_fwd", lb / 2)):
            parts.lathe(name, [(lr, 0), (lr + lw, 0), (lr + lw, ll), (lr, ll)], closed=True, segments=16,
                        location=(rr * math.cos(a), rr * math.sin(a), z), material="white_paint")

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
    z_servo = za + ml + 0.008                    # servos stand just forward of the mount: design
    # The payload's name on the lines of fins 1 and 3 (fin0 and fin2), reading up from just above each fin.
    paint = materials.colour(spec["materials"]["lettering"])
    img = textures.marking("finrocket_lettering", [(os.path.join(HARNESS, "refs", "finrocket", "lettering-mask.png"), paint)],
                           os.path.join(HARNESS, "out", "finrocket", "textures"))
    mat = materials.image("finrocket_lettering", img, metallic=0.0, roughness=0.6, cutout=True)
    w, h = d["lettering_length"], d["lettering_height"]
    zc = z_le + d["lettering_gap"] + w / 2
    for i in (0, 2):
        a = i * math.pi / 2
        with parts.assembly(f"lettering{i}"):
            parts.decal(f"lettering{i}", tube, center=(ro * math.cos(a), ro * math.sin(a), zc),
                        direction=(-math.cos(a), -math.sin(a), 0), up=(math.sin(a), -math.cos(a), 0),
                        width=w, height=h, material=mat)
    for i in range(4):
        a = i * math.pi / 2
        r_hat = (math.cos(a), math.sin(a), 0.0)
        t_hat = (-math.sin(a), math.cos(a), 0.0)  # z × radial
        R = lambda r, z, r_hat=r_hat: (r * r_hat[0], r * r_hat[1], z)
        with parts.assembly(f"fin{i}"):
            # The outer tip_band of the span painted: a separate surface on the same planform.
            ys = s - d["fin_tip_band"]
            cs, sws = cr + (ct - cr) * ys / s, sw * ys / s
            fin = parts.surface(f"fin{i}", R(ro + gap, z_le), cr, R(ro + gap + ys, z_le - sws), cs,
                                d["fin_thickness"] / cr, kind="lens", chord_dir=(0, 0, -1), material="black")
            tip = parts.surface(f"fin{i}_tip", R(ro + gap + ys, z_le - sws), cs, R(ro + gap + s, z_le - sw), ct,
                                d["fin_thickness"] / cr, kind="lens", chord_dir=(0, 0, -1), material="fin_tip")
            shaft = parts.tube(f"fin{i}_shaft", [R(ri - 0.006, z_piv), R(ro + gap + 0.004, z_piv)], 0.001,
                               segments=8, material="dark_metal")
            horn = parts.box(f"fin{i}_horn", (0.0015, 0.008, 0.003), location=R(ri - 0.005, z_piv),
                             direction=(0, 0, 1), roll_deg=math.degrees(a), material="dark_metal")
            parts.hinge(f"fin{i}_j", [fin, tip, shaft, horn], R(ri - 0.006, z_piv), R(ro + gap + s, z_piv),
                        sample=R(ro + gap, z_le - cr), want=tuple(-c for c in t_hat))
        with parts.assembly(f"servo{i}"):
            # Lying along the axis between the mount's front and the board, shaft pointing outward.
            r_c = ri - sz / 2 - 0.001
            # The fins sit on the x and y axes, so the box is sized in world axes: its height (sz)
            # along the radial line, its width (sy) across it, its length (sx) along the rocket.
            size = (sz, sy, sx) if i % 2 == 0 else (sy, sz, sx)
            parts.box(f"servo{i}", size, location=R(r_c, z_servo + sx / 2), material="dark_metal")
            horn_pt = R(ri - 0.004, z_servo + 0.004)
            parts.tube(f"pushrod{i}", [horn_pt, R(ri - 0.004, z_piv), R(ri - 0.005, z_piv)], 0.0005,
                       segments=6, material="foil_silver")
