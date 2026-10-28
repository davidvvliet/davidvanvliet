# X-15, the basic airplane. Built from lib/parts in metres. Every number comes from
# specs/x15.json: Table I of TN D-3343 for sizes (its "facts" and "dimensions") and the
# 1966 three-view for positions and shapes ("from_drawing", in feet, x aft from the nose tip).
# World frame: x forward with the fuselage base at x = 0, y left, z up.
import math
from lib import parts

FT = 0.3048

def build(spec):
    f, dr = {k: v["value"] for k, v in spec["facts"].items()}, spec["from_drawing"]
    length = spec["dimensions"]["overall_length"]["value"] / FT  # 49.5 ft

    def P(x, y, z):  # drawing feet -> world metres
        return ((length - x) * FT, y * FT, z * FT)

    def stations(rows):
        return [((length - x) * FT, w * FT, t * FT, b * FT) for x, w, t, b in rows]

    rows = dr["fuselage"]["stations"]
    cut = spec["from_photos"]["bare_nose_end_x"]["value"]
    i = next(k for k, r in enumerate(rows) if r[0] > cut)
    a, b = rows[i - 1], rows[i]
    t = (cut - a[0]) / (b[0] - a[0])
    mid = [cut] + [a[j] + (b[j] - a[j]) * t for j in (1, 2, 3)]
    with parts.assembly("fuselage", core=True):
        parts.fuselage("fuselage", stations([mid] + rows[i:]), n=40, material="x15_black")
    with parts.assembly("nose_cone"):
        parts.fuselage("nose_cone", stations(rows[:i] + [mid]), n=40, material="x15_bare")
        for sign, side in parts.sides():
            rows = [(x, w, t, b) for x, w, t, b in dr["side_fairings"]["stations"]]
            parts.loft(f"fairing_{side}", [[((length - x) * FT, sign * y * FT, z * FT)
                                            for y, z in parts.section(w, t, b, 32, 3.0)] for x, w, t, b in rows],
                       material="x15_black")

    with parts.assembly("canopy"):
        rings = []
        for x, w, t, b in dr["canopy"]["stations"]:
            if w <= 0:
                rings.append([P(x, 0, t)])
            else:
                rings.append([P(x, y, z) for y, z in parts.section(w, t, b, 32, 2.5)])
        parts.loft("canopy", rings, material="x15_black")

    with parts.assembly("ball_nose"):
        bn = f["ball_nose"]
        L, r = bn["length"], bn["base_diameter"] / 2
        # Round front (radius r) then straight back to the base.
        prof = [(0, 0)] + [(r * math.sin(a), r * (1 - math.cos(a)))
                           for a in (math.pi / 2 * k / 8 for k in range(1, 9))] + [(r, L), (0, L)]
        parts.lathe("ball_nose", prof, location=P(0, 0, dr["ball_nose"]["axis_z"]),
                    direction=(-1, 0, 0), material="x15_bare")

    def planform(fact, semispan, tip_le_x):
        """Root and tip leading-edge x (ft) from Table I chords and quarter-chord sweep,
        anchored on the drawing's tip leading edge."""
        cr, ct = fact["root_chord"] / FT, fact["tip_chord"] / FT
        tip_q = tip_le_x + ct / 4
        root_q = tip_q - semispan * math.tan(math.radians(fact["sweep_quarter_chord_deg"]))
        return root_q - cr / 4, cr, tip_le_x, ct

    span = spec["dimensions"]["wing_span"]["value"] / FT / 2
    rle, cr, tle, ct = planform(f["wing"], span, dr["wing"]["tip_le_x"])
    wz = dr["wing"]["z"]
    for sign, side in parts.sides():
        with parts.assembly(f"wing_{side}"):
            parts.surface(f"wing_{side}", P(rle, 0, wz), cr * FT, P(tle, sign * span, wz), ct * FT,
                          0.05, material="x15_black")
        pod = f["wingtip_pods"]
        pr, pl = pod["diameter"] / 2, pod["length"]
        mid_x = tle + ct * spec["from_photos"]["wingtip_pod_position"]["value"]["centre_chord_fraction"]
        nose = P(mid_x, sign * span, wz)
        nose = (nose[0] + pl / 2, nose[1], nose[2])
        # Shape (round nose, short taper aft) estimated from photos NASM2018-10035 and -10037.
        prof = [(0, 0)] + [(pr * math.sin(a), 1.5 * pr * (1 - math.cos(a)))
                           for a in (math.pi / 2 * k / 6 for k in range(1, 7))] + [(pr, pl - 2 * pr), (pr * 0.4, pl), (0, pl)]
        with parts.assembly(f"pod_{side}"):
            parts.lathe(f"pod_{side}", prof, location=nose, direction=(-1, 0, 0), segments=24, material="x15_black")

    ht = f["horizontal_tail"]
    hspan = spec["dimensions"]["horizontal_tail_span"]["value"] / FT / 2
    rle, cr, tle, ct = planform(ht, hspan, dr["horizontal_tail"]["tip_le_x"])
    dih = math.tan(math.radians(ht["dihedral_deg"]))
    z0 = dr["horizontal_tail"]["root_z_at_fairing"] - dr["horizontal_tail"]["fairing_y"] * dih
    for sign, side in parts.sides():
        with parts.assembly(f"htail_{side}"):
            parts.surface(f"htail_{side}", P(rle, 0, z0), cr * FT, P(tle, sign * hspan, z0 + hspan * dih),
                          ct * FT, 0.05, material="x15_black")

    # Fins: 10 deg single wedge, so the base is 2 tan 5 deg of the chord thick.
    wedge = 2 * math.tan(math.radians(5))
    fus = dr["fuselage"]["stations"]
    top, bottom = max(s[2] for s in fus), min(s[3] for s in fus)
    for name, fact, te, root_z, up in (("upper_fin", f["upper_vertical_tail"], dr["upper_vertical_tail"]["te_x"], top, 1),
                                       ("lower_fin", f["lower_vertical_tail"], dr["lower_vertical_tail"]["te_x"], bottom, -1)):
        cr, ct, sp = fact["root_chord"] / FT, fact["tip_chord"] / FT, fact["span"] / FT
        geom = (P(te - cr, 0, root_z), cr * FT, P(te - ct, 0, root_z + up * sp), ct * FT, wedge)
        with parts.assembly(name):
            parts.surface(name, *geom, kind="wedge", material="x15_black")
        # Speed brakes: the aft part of the fixed fin, a left and a right half that open apart.
        sb = f["speed_brakes"]
        span_frac = sb["mean_span"] / fact["span"]
        # A fixed fraction of the fin chord: Table I's 3.36 ft at the root, 9% less at the
        # brake's top, where the fin chord is shorter (area 5.1 vs Table I's 5.37 ft2).
        c = cr
        for sign, side in parts.sides():
            sname = f"speed_brake_{name.split('_')[0]}_{side}"
            with parts.assembly(sname):
                # side +1 is along (tip - root) x aft: +y (left) for the upper fin, -y for the lower.
                parts.surface(sname, *geom, kind="wedge", span=(0, span_frac),
                              chord=(1 - sb["chord"] / FT / c, 1), side=sign * up, offset=0.004,
                              material="x15_black")
        if up > 0:
            with parts.assembly("fin_band"):
                parts.surface("fin_band", *geom, kind="wedge",
                              span=(spec["from_photos"]["yellow_band"]["value"]["from_span_fraction"], 1),
                              offset=0.003, material="x15_yellow")
