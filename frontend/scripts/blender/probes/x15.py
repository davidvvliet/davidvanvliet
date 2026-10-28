# X-15, the basic airplane. Built from lib/parts in metres. Every number comes from
# specs/x15.json: Table I of TN D-3343 for sizes (its "facts" and "dimensions") and the
# 1966 three-view for positions and shapes ("from_drawing", in feet, x aft from the nose tip).
# World frame: x forward with the fuselage base at x = 0, y left, z up.
import math
import bpy
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
        body_obj = parts.loft("fuselage", [ring(x) for x in xs], material="x15_black")
        # The engine's nozzle in the base (photo NASM-SI-2008-5570, straight from behind, camera
        # fitted): a bare plate, a red rim and the liner running forward into the fuselage.
        # The fairings end in a flat step (drawing, x 48.8 ft; photo NASM-SI-2008-5570 shows
        # flat ribbed end faces): those faces are shaded flat, not rounded into the body.
        x_end = P(fair[-1][0], 0, 0)[0]
        for face in body_obj.data.polygons:
            vx = [body_obj.data.vertices[i].co.x for i in face.vertices]
            if max(vx) <= x_end + 1e-4 and min(vx) >= x_end - 0.01:
                face.use_smooth = False
        nz = spec["from_photos"]["nozzle"]["value"]
        # The nozzle sits in the middle of the base's outline (photo NASM-SI-2008-5570: an even
        # black rim all round the bare plate), which is below the axis: the drawing's last
        # station reaches higher below the axis than above it.
        base = dr["fuselage"]["stations"][-1]
        nz_z = (base[2] + base[3]) / 2
        parts.cap_hole(body_obj, P(xs[-1], 0, nz_z), (-1, 0, 0), nz["plate_outer_r"])
    # Ribs across the fairings' flat end faces (photo NASM-SI-2008-5570): bars standing out of
    # the face, each cut to the face's width at its height (between the body and the fairing).
    rb = spec["from_photos"]["fairing_end_ribs"]["value"]
    outer, inner = ring(fair[-1][0]), ring(fair[-1][0] + 0.01)

    def reach(pts, z):
        """Furthest y (left side) where the section outline crosses height z, or None."""
        ys = []
        for (_, y0, z0), (_, y1, z1) in zip(pts, pts[1:] + pts[:1]):
            if (z0 - z) * (z1 - z) <= 0 and z0 != z1:
                ys.append(y0 + (y1 - y0) * (z - z0) / (z1 - z0))
        return max(ys) if ys else None

    zs = [p[2] for p in outer]
    ribs = []
    z = min(zs) + rb["spacing"] / 2
    while z < max(zs):
        yo, yi = reach(outer, z), reach(inner, z)
        yi = yi if yi is not None else 0.0
        if yo is not None and yo - yi > 0.03:
            for sgn in (1, -1):
                ribs.append(((rb["proud"], yo - yi - 0.01, rb["height"]),
                             (x_end - rb["proud"] / 2, sgn * (yo + yi) / 2, z)))
        z += rb["spacing"]
    with parts.assembly("fairing_ribs"):
        parts.boxes("fairing_ribs", ribs, material="x15_rib")
    with parts.assembly("nozzle"):
        x0, t = xs[-1], 0.02
        parts.lathe("nozzle_plate", [(nz["plate_outer_r"], 0), (nz["plate_outer_r"], t), (nz["rim_r"], t), (nz["rim_r"], 0)],
                    location=P(x0, 0, nz_z), direction=(1, 0, 0), segments=64, closed=True, material="x15_nozzle_plate", smooth=False)
        parts.lathe("nozzle_rim", [(nz["rim_r"], -0.01), (nz["rim_r"], 0.03), (nz["rim_r"] - 0.017, 0.03), (nz["rim_r"] - 0.017, -0.01)],
                    location=P(x0, 0, nz_z), direction=(1, 0, 0), segments=64, closed=True, material="x15_nozzle_rim", smooth=False)
        L, rt = nz["depth"], nz["throat_r"]
        rl = nz["rim_r"] - 0.017
        parts.lathe("nozzle_liner", [(rl, 0.03), (rt, L), (rt + t, L), (rl + t, 0.03)],
                    location=P(x0, 0, nz_z), direction=(1, 0, 0), segments=64, closed=True, material="x15_nozzle_liner")
        parts.lathe("nozzle_throat", [(0, L - 0.01), (rt + t, L - 0.01), (rt + t, L + 0.01), (0, L + 0.01)],
                    location=P(x0, 0, nz_z), direction=(1, 0, 0), segments=32, material="x15_black")

    # Canopy (photos NASM-SI-2007-12573, -12578, NASM-SI-2008-5563, -5565): a round tube (upright
    # sides under the front view's arch) whose front is a sharp V: two flat faces cut back from the
    # ridge (the side view's top line) at the top view's angle, carrying the side windows. Aft of the frame the
    # fairing is a roof over a base inside the fuselage. Edges where the surface turns sharply
    # are marked hard, so the hood has crisp lines between smooth faces.
    cs, arch = dr["canopy"], dr["canopy"]["arch"]
    ct = spec["from_photos"]["canopy_top"]["value"]  # the drawn top line, raised to the photos
    x_front, x_end = ct["top"][0][0], ct["top"][-1][0]
    (r0x, r0z), (r1x, r1z) = ct["top"][0], ct["top"][1]
    rake = (r1x - r0x) / (r1z - r0z)  # ridge: ft aft per ft up

    # The top line: straight between the given points, except the last span, from the roof's end
    # down to the spine, which is one S-curve, level at both ends, so the hood runs smoothly
    # into the fuselage.
    (xr, zr), (xe, ze) = ct["top"][-2], ct["top"][-1]
    top_line = [tuple(r) for r in ct["top"][:-1]] + [
        (xr + (xe - xr) * i / 24, zr + (ze - zr) * (3 * (i / 24) ** 2 - 2 * (i / 24) ** 3)) for i in range(1, 25)]

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

    def resample(pts, n):
        """n points evenly spaced along a polyline, keeping both ends."""
        if len(pts) == 1:
            return [pts[0]] * n
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

    def plane_y(x, z):  # a front face's half-width at station x, height z
        return (x - ridge_x(z)) * k

    def profile(x, n=48):
        """One side of the section at x, bottom to top (y, z), n points: the arch clipped by the
        front face's plane, so the face is exactly flat and fades out where the plane leaves the
        hood. Each corner where arch and face meet is a vertex, so the edge between them runs
        cleanly along the hood."""
        fx = cs["frame_x"]
        top = max(at(top_line, x), r1z if x < r1x else 0)
        if x <= fx:
            a, base = at(arch["half_width"], x), at(cs["sill"], x)
        else:  # aft fairing: the same arch, narrowing as the drawn fairing does
            a = at(cs["fairing_half_width"], x) * at(arch["half_width"], fx) / at(cs["fairing_half_width"], fx)
            base = at(cs["sill"], fx)
        zs = min(arch["z_shoulder"], top - 0.02)
        dense = [(a, base + (zs - base) * i / 20) for i in range(20)]
        dense += [(a * math.cos(t), zs + (top - zs) * math.sin(t)) for t in (math.pi / 2 * i / 200 for i in range(201))]
        z_ridge = r0z + (x - r0x) / rake  # where the two faces meet on the centreline
        arc = [q for q in dense if q[1] < z_ridge] + [dense[-1] if dense[-1][1] < z_ridge else (0.0, z_ridge)]
        f = [y - max(0.0, plane_y(x, z)) for y, z in arc]  # > 0 where the arch is outside the plane
        # The section is three pieces with fixed point counts, so every station has the same
        # layout: arch below the face, the face (on the plane), arch above it. A piece that isn't
        # there has zero length: with no face, both corners sit where the plane comes nearest.
        def cross(i):  # point between arc[i] and arc[i + 1] where f changes sign
            t = f[i] / (f[i] - f[i + 1])
            return (i, (arc[i][0] + (arc[i + 1][0] - arc[i][0]) * t, arc[i][1] + (arc[i + 1][1] - arc[i][1]) * t))
        ups = [cross(i) for i in range(len(arc) - 1) if f[i] <= 0 < f[i + 1]]
        downs = [cross(i) for i in range(len(arc) - 1) if f[i] > 0 >= f[i + 1]]
        if f[0] > 0:
            c1 = (-1, (max(0.0, plane_y(x, arc[0][1])), arc[0][1]))
        elif ups:
            c1 = ups[0]
        else:
            i = max(range(len(arc)), key=lambda j: f[j])
            c1 = (i - 1, arc[i])
        later = [d for d in downs if d[0] >= c1[0]]
        c2 = later[0] if later and (ups or f[0] > 0) else (c1 if not ups and f[0] <= 0 else (len(arc) - 1, (0.0, arc[-1][1])))
        i1, p1 = c1
        i2, p2 = c2
        below = arc[:i1 + 1] + [p1]
        face = [p1] + [(max(0.0, plane_y(x, z)), z) for _, z in arc[i1 + 1:i2 + 1]] + [p2]
        above = [p2] + arc[i2 + 1:]
        n1, n2 = n // 2, n // 4
        n3 = n - n1 - n2 + 2
        return resample(below, n1) + resample(face, n2)[1:] + resample(above, n3)[1:]

    def canopy_ring(x):
        half = profile(x)
        right = [(-y, z) for y, z in half]
        left = [(y, z) for y, z in reversed(half[:-1])]
        return [P(x, y, z) for y, z in right + left]

    def mark_hard_edges(obj, degrees=25):
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(degrees):
                e.smooth = False
        bm.to_mesh(obj.data)
        bm.free()

    cxs = [x_front + (x_end - x_front) * i / 80 for i in range(81)]
    with parts.assembly("canopy"):
        hood = parts.loft("canopy", [[P(x_front - 0.05, 0, r0z - 0.03)]] + [canopy_ring(x) for x in cxs[1:-1]]
                          + [[P(x_end, 0, ct["top"][-1][1])]], material="x15_black")
        mark_hard_edges(hood)

    # Windows, one each side on the hood's front face (photos): the photo-fitted outline projected
    # sideways onto the hood, as a thin pane standing a few millimetres out of it (a separate
    # solid, so it never flickers) inside a raised frame, so the glass sits recessed.
    win = spec["from_photos"]["canopy_window"]["value"]["outline"]
    wf = spec["from_photos"]["window_frame"]["value"]

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

    def z_span(x):
        """Lowest and highest z of the window outline at x."""
        zs = [z0 + (z1 - z0) * (x - x0) / (x1 - x0) for (x0, z0), (x1, z1) in zip(win, win[1:] + win[:1])
              if min(x0, x1) <= x <= max(x0, x1) and x1 != x0]
        return min(zs), min(max(zs), at(top_line, x) - 0.05)

    def frame(name, outline, surf):
        """A raised band round a closed 2D outline, mapped onto the hood by surf(u, v, out)."""
        for _ in range(2):  # round the corners first, so the band never folds over itself
            outline = [q for a, b in zip(outline, outline[1:] + outline[:1]) for q in
                       ((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]),
                        (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))]
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

    pane = 0.02  # ft out of the hood
    wx0, wx1 = min(x for x, _ in win) + 0.01, max(x for x, _ in win) - 0.01
    side_outline = []  # the outline with each edge split every 0.1 ft, so it follows the hood
    for (u0, v0), (u1, v1) in zip(win, win[1:] + win[:1]):
        n = max(1, round(math.hypot(u1 - u0, v1 - v0) / 0.1))
        side_outline += [(u0 + (u1 - u0) * i / n, v0 + (v1 - v0) * i / n) for i in range(n)]
    for sign, side_name in parts.sides():
        rings = []
        for i in range(24):
            x = wx0 + (wx1 - wx0) * i / 23
            zb, zt = z_span(x)
            zt = max(zt, zb + 0.01)
            zs = [zb + (zt - zb) * j / 9 for j in range(10)]
            rings.append([on_side(x, z, sign, pane) for z in zs] + [on_side(x, z, sign, -pane) for z in reversed(zs)])
        with parts.assembly(f"window_{side_name}"):
            parts.loft(f"window_{side_name}", rings, material="x15_glass", smooth=False)
        with parts.assembly(f"window_frame_{side_name}"):
            frame(f"window_frame_{side_name}", side_outline,
                  lambda u, v, out, sign=sign: on_side(u, min(v, at(top_line, u) - 0.02), sign, out))

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
    # Each wing's plain flap (Table I: span, inboard and outboard chord) runs out from the side
    # of the fuselage along the trailing edge (1966 three-view top view). The wing is built
    # round it in pieces that meet edge to edge and are joined into one object; the flap is its
    # own object, a hinge gap ahead of it and beside its outer end.
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    fl, gap = f["flap"], 0.01 / FT
    le = lambda s: rle + (tle - rle) * s
    chord = lambda s: cr + (ct - cr) * s
    te = lambda s: le(s) + chord(s)
    bvh = BVHTree.FromObject(body_obj, bpy.context.evaluated_depsgraph_get())
    for sign, side in parts.sides():
        # The flap's inner end: where the trailing edge meets the fuselage's side.
        x_in = P(te(0.3) - 0.2, 0, wz)
        hit = bvh.ray_cast(Vector((x_in[0], sign * 3.0, x_in[2])), Vector((0, -sign, 0)), 6.0)[0]
        s_in = abs(hit.y) / FT / span
        s_out = s_in + fl["span_each"] / FT / span
        hinge_in, hinge_out = te(s_in) - fl["inboard_chord"] / FT, te(s_out) - fl["outboard_chord"] / FT
        hinge = lambda s: hinge_in + (hinge_out - hinge_in) * (s - s_in) / (s_out - s_in)
        frac = lambda s, dx=0.0: (hinge(s) + dx - le(s)) / chord(s)
        geom = (P(rle, 0, wz), cr * FT, P(tle, sign * span, wz), ct * FT, 0.05)
        with parts.assembly(f"wing_{side}"):
            pieces = [parts.surface(f"wing_{side}", *geom, span=(0, s_in), material="x15_black"),
                      parts.surface("_wing_fixed", *geom, span=(s_in, s_out),
                                    chord=((0, frac(s_in)), (0, frac(s_out))), material="x15_black"),
                      parts.surface("_wing_outer", *geom, span=(s_out, 1), material="x15_black")]
            bm = bmesh.new()
            for o in pieces:
                bm.from_mesh(o.data)
            bm.to_mesh(pieces[0].data); bm.free()
            for o in pieces[1:]:
                bpy.data.objects.remove(o)
            s_end = s_out - gap / span
            parts.surface(f"flap_{side}", *geom, span=(s_in, s_end),
                          chord=((frac(s_in, gap), 1), (frac(s_end, gap), 1)), material="x15_black")

    ht = f["horizontal_tail"]
    hspan = spec["dimensions"]["horizontal_tail_span"]["value"] / FT / 2
    rle, cr, tle, ct = planform(ht, hspan, dr["horizontal_tail"]["tip_le_x"])
    dih = math.tan(math.radians(ht["dihedral_deg"]))
    z0 = dr["horizontal_tail"]["root_z_at_fairing"] - dr["horizontal_tail"]["fairing_y"] * dih
    for sign, side in parts.sides():
        with parts.assembly(f"htail_{side}"):
            tail = parts.surface(f"htail_{side}", P(rle, 0, z0), cr * FT, P(tle, sign * hspan, z0 + hspan * dih),
                                 ct * FT, 0.05, material=["x15_black", "x15_tail_bare"])
            # Bare metal underneath, black on top (spec materials x15_tail_bare).
            for face in tail.data.polygons:
                face.material_index = 1 if face.normal.z < 0 else 0

    # Fins: 10 deg single wedge, so the base is 2 tan 5 deg of the chord thick.
    wedge = 2 * math.tan(math.radians(5))
    fus = dr["fuselage"]["stations"]
    top, bottom = max(s[2] for s in fus), min(s[3] for s in fus)
    for name, fact, te, root_z, up in (("upper_fin", f["upper_vertical_tail"], dr["upper_vertical_tail"]["te_x"], top, 1),
                                       ("lower_fin", f["lower_vertical_tail"], dr["lower_vertical_tail"]["te_x"], bottom, -1)):
        cr, ct, sp = fact["root_chord"] / FT, fact["tip_chord"] / FT, fact["span"] / FT
        # Table I's root chord and span are the fin's exposed part, from the fuselage's top (or
        # bottom). The fin's flat sides carry on down into the round fuselage (photos
        # NASM-SI-2007-12585, -12586) to just inside its skin (not further: the nozzle runs
        # forward inside), so its planform is extended inward that far; every piece's span
        # fraction below is mapped onto that, keeping its exposed size.
        from mathutils import Vector
        from mathutils.bvhtree import BVHTree
        bvh = BVHTree.FromObject(body_obj, bpy.context.evaluated_depsgraph_get())

        def skin(x0, x1):
            """Lowest skin (distance from the axis, m) beside the fin between world x0 and x1."""
            hits = []
            for k in range(9):
                x = x0 + (x1 - x0) * k / 8
                for yy in (0.3, -0.3):
                    hit = bvh.ray_cast(Vector((x, yy, up * 3.0)), Vector((0, 0, -up)), 6.0)[0]
                    if hit is not None:
                        hits.append(up * hit.z)
            return min(hits)

        inner = (skin(P(te, 0, 0)[0], P(te - cr, 0, 0)[0]) - 0.05) / FT
        d0 = up * root_z - inner
        sp_in, cr_in = sp + d0, cr + (cr - ct) * d0 / sp
        geom = (P(te - cr_in, 0, up * inner), cr_in * FT, P(te - ct, 0, root_z + up * sp), ct * FT, wedge)
        frac = lambda fr: (d0 + fr * sp) / sp_in
        # The fin is built from pieces that meet edge to edge (no surface laid over another,
        # which flickers in the viewer): the fixed part ahead of the speed brakes, the brakes
        # (a left and a right half that open apart), the rest of the fin above them, and on
        # the upper fin the yellow moving part.
        sb = f["speed_brakes"]
        brake_top = frac(sb["mean_span"] / fact["span"])
        # The brakes reach down to the skin beside the fin (lower there than on the top line,
        # the body being round); Table I's brake chord is taken there (their longest chord).
        brake_le = 1 - sb["chord"] / FT / cr
        root_f = ((skin(P(te, 0, 0)[0], P(te - cr * (1 - brake_le), 0, 0)[0]) - 0.02) / FT - inner) / sp_in
        brake_le = 1 - sb["chord"] / FT / (cr_in + (ct - cr_in) * root_f)
        band = frac(spec["from_photos"]["yellow_band"]["value"]["from_span_fraction"]) if up > 0 else 1.0
        with parts.assembly(name):
            parts.surface(name, *geom, kind="wedge", span=(0, brake_top), chord=(0, brake_le),
                          material="x15_black")
            parts.surface(f"{name}_upper" if up > 0 else f"{name}_lower", *geom, kind="wedge",
                          span=(brake_top, band), material="x15_black")
            # Behind the hinge line, below the brakes: solid fin inside the fuselage.
            parts.surface(f"{name}_root", *geom, kind="wedge", span=(0, root_f), chord=(brake_le, 1),
                          material="x15_black")
        for sign, side in parts.sides():
            sname = f"speed_brake_{name.split('_')[0]}_{side}"
            with parts.assembly(sname):
                # side +1 is along (tip - root) x aft: -y (right) on the upper fin, +y on the lower.
                brake = parts.surface(sname, *geom, kind="wedge", span=(root_f, brake_top), chord=(brake_le, 1),
                                      side=-sign * up, material="x15_black")
                # Each brake is a plate: behind it the fin is an open slot back to the fixed
                # part (photos NASM-SI-2007-12585, -12586 and NASM-SI-2008-5570).
                parts.shell(brake, lambda face, vs: all(abs(v.y) > 1e-4 for v in vs),
                            spec["from_photos"]["speed_brake_plate"]["value"]["thickness_m"])
        if up > 0:
            with parts.assembly("fin_band"):
                box_part = parts.surface("fin_band", *geom, kind="wedge", span=(band, 1), material="x15_black")
            # The moving part's blunt back face is ribbed like the fairing ends (photo
            # NASM-SI-2007-12585: ribs every 21.5 px over the face's 623 px = 0.87 m, so 3 cm).
            rb = spec["from_photos"]["fairing_end_ribs"]["value"]
            te = [box_part.matrix_world @ v.co for v in box_part.data.vertices]
            x_te = min(v.x for v in te)
            edge = [v for v in te if v.x < x_te + 1e-4]
            z0, z1 = min(v.z for v in edge), max(v.z for v in edge)
            half = lambda zz: max(abs(v.y) for v in edge if abs(v.z - zz) < 1e-3)
            h0, h1 = half(z0), half(z1)
            ribs = []
            zz = z0 + rb["spacing"] / 2
            while zz < z1 - rb["height"] / 2:
                hw = h0 + (h1 - h0) * (zz - z0) / (z1 - z0)
                ribs.append(((rb["proud"], 2 * hw - 0.01, rb["height"]), (x_te - rb["proud"] / 2, 0, zz)))
                zz += rb["spacing"]
            with parts.assembly("fin_ribs"):
                parts.boxes("fin_ribs", ribs, material="x15_rib")
