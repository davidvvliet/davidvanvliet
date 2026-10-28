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

    # Canopy (photos NASM-SI-2007-12573, -12578, NASM-SI-2008-5563, -5565): a hood of upright
    # sides under a round roof (the front view's arch), whose front is two flat windscreen faces
    # cut back from the centre-post ridge (the side view's top line). Aft of the frame the
    # fairing is a roof over a base inside the fuselage. Edges where the surface turns sharply
    # are marked hard, so the hood has crisp lines between smooth faces.
    cs, cw, arch = dr["canopy"], dr["canopy_windows"], dr["canopy"]["arch"]
    x_front, x_end = cs["top"][0][0], cs["top"][-1][0]
    (r0x, r0z), (r1x, r1z) = cs["top"][0], cs["top"][1]
    rake = (r1x - r0x) / (r1z - r0z)  # ridge: ft aft per ft up
    k = cs["windscreen_plan_tan"]

    def at(rows, x):
        if x <= rows[0][0]:
            return rows[0][1]
        if x >= rows[-1][0]:
            return rows[-1][1]
        for (x0, v0), (x1, v1) in zip(rows, rows[1:]):
            if x0 <= x <= x1:
                return v0 + (v1 - v0) * (x - x0) / (x1 - x0)

    def ridge_x(z):
        return r0x + (z - r0z) * rake

    def profile(x, n=64):
        """One side of the section at x, bottom to top, densely sampled (y, z)."""
        fx = cs["frame_x"]
        top = max(at(cs["top"], x), r1z if x < r1x else 0)
        if x <= fx:
            a, base = at(arch["half_width"], x), at(cs["sill"], x)
        else:  # aft fairing: the same arch, narrowing as the drawn fairing does
            a = at(cs["fairing_half_width"], x) * at(arch["half_width"], fx) / at(cs["fairing_half_width"], fx)
            base = at(cs["sill"], fx)
        zs = min(arch["z_shoulder"], top - 0.02)
        pts = [(a, base + (zs - base) * i / 8) for i in range(8)]
        pts += [(a * math.cos(t), zs + (top - zs) * math.sin(t)) for t in (math.pi / 2 * i / (n - 8) for i in range(n - 7))]
        out = []
        for y, z in pts:  # the windscreen faces: no wider than they allow at this height
            y = min(y, max(0.0, (x - ridge_x(z)) * k))
            out.append((y, z))
            if y == 0.0:
                break
        return out

    def resample(pts, n=40):
        d = [0.0]
        for (y0, z0), (y1, z1) in zip(pts, pts[1:]):
            d.append(d[-1] + math.hypot(y1 - y0, z1 - z0))
        res = []
        for i in range(n):
            s = d[-1] * i / (n - 1)
            for j in range(len(pts) - 1):
                if d[j] <= s <= d[j + 1] or j == len(pts) - 2:
                    t = (s - d[j]) / (d[j + 1] - d[j]) if d[j + 1] > d[j] else 0
                    res.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * t, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * t))
                    break
        return res

    def canopy_ring(x):
        half = resample(profile(x))
        right = [(-y, z) for y, z in half]
        left = [(y, z) for y, z in reversed(half[:-1])]
        return [P(x, y, z) for y, z in right + left]

    def mark_hard_edges(obj, degrees=25):
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(degrees):
                e.smooth = False
        bm.to_mesh(obj.data)
        bm.free()

    cxs = [x_front + (x_end - x_front) * i / 80 for i in range(81)]
    with parts.assembly("canopy"):
        hood = parts.loft("canopy", [[P(x_front - 0.05, 0, r0z - 0.03)]] + [canopy_ring(x) for x in cxs[1:-1]]
                          + [[P(x_end, 0, cs["top"][-1][1])]], material="x15_black")
        mark_hard_edges(hood)

    # Windows, two each side: a windscreen pane on the front face (the front view's D outline,
    # projected aft onto the face) and a side window behind it (the side view's outline,
    # projected sideways onto the side). Each is a thin pane standing a few millimetres out of
    # the hood (a separate solid, so it never flickers) inside a raised frame (photos).
    (xa, za), (xb, zb) = cw["front_low"], cw["front_high"]
    ws, wf = dr["windscreen"], spec["from_photos"]["window_frame"]["value"]

    def on_side(x, z, sign, out):
        pts = profile(x)
        for (y0, z0), (y1, z1) in zip(pts, pts[1:]):
            if z0 <= z <= z1 and z1 > z0:
                t = (z - z0) / (z1 - z0)
                y = y0 + (y1 - y0) * t
                ny, nz = (z1 - z0), -(y1 - y0)
                n = math.hypot(ny, nz)
                return P(x, sign * (y + out * ny / n), z + out * nz / n)
        raise ValueError(f"window point off the canopy: x {x}, z {z}")

    face_n = (-k, 1.0, k * rake)  # outward normal of a windscreen face: forward, out and up
    face_len = math.sqrt(sum(c * c for c in face_n))

    def on_face(y, z, sign, out):
        x = ridge_x(z) + y / k
        nx, ny, nz = (c / face_len for c in face_n)
        return P(x + out * nx, sign * (y + out * ny), z + out * nz)

    def z_top(x):
        front = za + (x - xa) * (zb - za) / (xb - xa)
        return min(cw["z_high"], front, at(cs["top"], x) - 0.05)

    def ws_half(z):  # the windscreen's front-view outline: straight sides, then a round top
        c, h = (ws["y_inner"] + ws["y_outer"]) / 2, (ws["y_outer"] - ws["y_inner"]) / 2
        if z <= ws["z_side_top"]:
            return c, h
        t = (z - ws["z_side_top"]) / (ws["z_top"] - ws["z_side_top"])
        return c, h * math.sqrt(max(0.0, 1 - t * t))

    def frame(name, outline, surf):
        """A raised band round a closed 2D outline, mapped onto the hood by surf(u, v, out)."""
        m = len(outline)
        area = sum(u0 * v1 - u1 * v0 for (u0, v0), (u1, v1) in zip(outline, outline[1:] + outline[:1]))
        turn = 1 if area > 0 else -1  # anticlockwise: outward is the tangent turned clockwise
        rings = []
        for i in range(m + 1):
            (up, vp), (un, vn) = outline[(i - 1) % m], outline[(i + 1) % m]
            u, v = outline[i % m]
            tu, tv = un - up, vn - vp
            t = math.hypot(tu, tv)
            nu, nv = turn * tv / t, -turn * tu / t
            ui, vi = u - 0.01 * nu, v - 0.01 * nv
            uo, vo = u + wf["width"] * nu, v + wf["width"] * nv
            rings.append([surf(ui, vi, -0.01), surf(ui, vi, wf["height"]),
                          surf(uo, vo, wf["height"]), surf(uo, vo, -0.01)])
        parts.loft(name, rings, material="x15_black", smooth=False)

    x0 = xa + (cw["z_low"] - za) * (xb - xa) / (zb - za) + 0.02
    pane = 0.02  # ft out of the hood
    xs_w = [x0 + (cw["aft_x"] - x0) * i / 24 for i in range(25)]
    side_outline = ([(x, cw["z_low"]) for x in xs_w[:-1]]
                    + [(cw["aft_x"], cw["z_low"] + (z_top(cw["aft_x"]) - cw["z_low"]) * i / 6) for i in range(6)]
                    + [(x, max(z_top(x), cw["z_low"] + 0.01)) for x in reversed(xs_w[1:])])
    zw = [ws["z_low"] + (ws["z_top"] - 0.005 - ws["z_low"]) * i / 14 for i in range(15)]
    ws_outline = ([(sum(ws_half(z)), z) for z in zw] + [(ws_half(z)[0] - ws_half(z)[1], z) for z in reversed(zw)])
    for sign, side_name in parts.sides():
        rings = []
        for i in range(16):
            x = x0 + (cw["aft_x"] - x0) * i / 15
            zt = max(z_top(x), cw["z_low"] + 0.01)
            zs = [cw["z_low"] + (zt - cw["z_low"]) * j / 9 for j in range(10)]
            rings.append([on_side(x, z, sign, pane) for z in zs] + [on_side(x, z, sign, -pane) for z in reversed(zs)])
        with parts.assembly(f"window_{side_name}"):
            parts.loft(f"window_{side_name}", rings, material="x15_glass", smooth=False)
        rings = []
        for z in zw:
            c, h = ws_half(z)
            ys = [c - h + 2 * h * j / 9 for j in range(10)]
            rings.append([on_face(y, z, sign, pane) for y in ys] + [on_face(y, z, sign, -pane) for y in reversed(ys)])
        with parts.assembly(f"windscreen_{side_name}"):
            parts.loft(f"windscreen_{side_name}", rings, material="x15_glass", smooth=False)
        with parts.assembly(f"window_frame_{side_name}"):
            frame(f"window_frame_{side_name}", side_outline,
                  lambda u, v, out, sign=sign: on_side(u, min(v, at(cs["top"], u) - 0.02), sign, out))
        with parts.assembly(f"windscreen_frame_{side_name}"):
            frame(f"windscreen_frame_{side_name}", ws_outline, lambda u, v, out, sign=sign: on_face(u, v, sign, out))

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
