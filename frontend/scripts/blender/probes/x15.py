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

    # Body and side fairings are one skin: each cross-section is the smooth union of the body
    # (an ellipse) and the fairing band (a superellipse across the full width), so the two
    # blend with a fillet as in the drawing's front view. Fillet size estimated from that view.
    body, fair = dr["fuselage"]["stations"], dr["side_fairings"]["stations"]
    fillet = dr["side_fairings"]["fillet"]

    def lerp(rows, x):
        if x < rows[0][0] or x > rows[-1][0]:
            return None
        for r0, r1 in zip(rows, rows[1:]):
            if r0[0] <= x <= r1[0]:
                t = (x - r0[0]) / (r1[0] - r0[0]) if r1[0] > r0[0] else 0
                return [u + (v - u) * t for u, v in zip(r0[1:], r1[1:])]

    def field(y, z, w, top, bot, n):
        h, zc = (top - bot) / 2, (top + bot) / 2
        return ((abs(y / w) ** n + abs((z - zc) / h) ** n) ** (1 / n) - 1) * min(w, h)

    rn = spec["from_photos"]["round_nose"]["value"]
    ball_r = f["ball_nose"]["base_diameter"] / FT / 2

    def ring(x, n=64):
        w, top, bot = lerp(body, x)
        if x < rn["blend_to_x"]:  # round nose cone, from the ball's base
            zc, r = (top + bot) / 2, (w + (top - bot) / 2) / 2
            if x <= body[0][0]:
                r = ball_r
            t = max(0.0, (x - rn["until_x"]) / (rn["blend_to_x"] - rn["until_x"]))
            w, top, bot = r + (w - r) * t, zc + r + (top - zc - r) * t, zc - r + (bot - zc + r) * t
        fr = lerp(fair, x)
        zc = (top + bot) / 2
        if fr:  # under the fairings the body is narrower than the plan outline (front view)
            ramp = min(1.0, (x - fair[0][0]) / (dr["side_fairings"]["body_narrowing_to_x"] - fair[0][0]))
            w *= 1 - (1 - dr["side_fairings"]["body_width_factor"]) * ramp
        def f(y, z):
            d = field(y, z, w, top, bot, 2)
            if fr:
                e = field(y, z, fr[0], fr[1], fr[2], dr["side_fairings"]["exponent"])
                h = max(fillet - abs(d - e), 0.0) / fillet  # polynomial smooth min: blends only near the join
                d = min(d, e) - h * h * fillet / 4
            return d
        pts = []
        for k in range(n):
            a = math.pi / 2 + 2 * math.pi * k / n
            dy, dz = math.cos(a), math.sin(a)
            lo, hi = 0.0, 8.0
            for _ in range(40):  # bisect along the ray for the surface
                m = (lo + hi) / 2
                lo, hi = (m, hi) if f(m * dy, zc + m * dz) < 0 else (lo, m)
            pts.append(P(x, lo * dy, zc + lo * dz))
        return pts

    xs = sorted({r[0] for r in body} | {r[0] for r in fair} | {2.5, 3.5, 4.25, 7.0, rn["blend_to_x"], 15.0, 17.0, fair[-1][0] + 0.01})
    with parts.assembly("fuselage", core=True):
        parts.loft("fuselage", [ring(x) for x in xs], material="x15_black")

    with parts.assembly("canopy"):
        rings = []
        for x, w, t, b in dr["canopy"]["stations"]:
            if w <= 0:
                rings.append([P(x, 0, t)])
            else:
                rings.append([P(x, y, z) for y, z in parts.section(w, t, b, 32, dr["canopy"]["exponent"])])
        parts.loft("canopy", rings, material="x15_black")

    with parts.assembly("ball_nose"):
        # The sensor: a sphere in a lip, then a straight cone (its afterbody) to the base,
        # which meets the fuselage's first station.
        bn, shape = f["ball_nose"], spec["from_photos"]["ball_nose_shape"]["value"]
        L, rb, rs = bn["length"], bn["base_diameter"] / 2, bn["sphere_diameter"] / 2
        lip_z = shape["lip_from_tip_sphere_diameters"] * 2 * rs
        a_end = math.acos(1 - lip_z / rs)  # where the sphere meets the lip
        prof = [(0, 0)] + [(rs * math.sin(a), rs * (1 - math.cos(a)))
                           for a in (a_end * k / 10 for k in range(1, 11))]
        prof += [(rs * shape["lip_radius_factor"], lip_z), (rb, L), (0, L)]
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
        # The fin is built from pieces that meet edge to edge (no surface laid over another,
        # which flickers in the viewer): the fixed part ahead of the speed brakes, the brakes
        # (a left and a right half that open apart), the rest of the fin above them, and on
        # the upper fin the yellow moving part.
        sb = f["speed_brakes"]
        brake_top = sb["mean_span"] / fact["span"]
        # The brakes take a fixed fraction of the fin chord: Table I's 3.36 ft at the root, 9%
        # less at their top, where the fin chord is shorter (area 5.1 vs Table I's 5.37 ft2).
        brake_le = 1 - sb["chord"] / FT / cr
        band = spec["from_photos"]["yellow_band"]["value"]["from_span_fraction"] if up > 0 else 1.0
        with parts.assembly(name):
            parts.surface(name, *geom, kind="wedge", span=(0, brake_top), chord=(0, brake_le),
                          material="x15_black")
            parts.surface(f"{name}_upper" if up > 0 else f"{name}_lower", *geom, kind="wedge",
                          span=(brake_top, band), material="x15_black")
        for sign, side in parts.sides():
            sname = f"speed_brake_{name.split('_')[0]}_{side}"
            with parts.assembly(sname):
                # side +1 is along (tip - root) x aft: -y (right) on the upper fin, +y on the lower.
                parts.surface(sname, *geom, kind="wedge", span=(0, brake_top), chord=(brake_le, 1),
                              side=-sign * up, material="x15_black")
        if up > 0:
            with parts.assembly("fin_band"):
                parts.surface("fin_band", *geom, kind="wedge", span=(band, 1), material="x15_yellow")
