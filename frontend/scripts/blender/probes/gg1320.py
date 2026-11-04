# Honeywell GG1320AN ring laser gyro. Built from lib/parts in metres; every number comes from
# specs/gg1320.json (with its source) or is marked here as estimated.
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from lib import materials, parts

# Corner and face directions of the block, in degrees from +X (sam_gg1320an's labelled photo:
# mirror 2 at the top, mirrors 1 and 3 bottom left and right; cathode on the bottom face,
# anode 1 on the right upper face, anode 2 on the left).
CORNERS = {"mirror_1": 210.0, "mirror_2": 90.0, "mirror_3": 330.0}
FACES = {"cathode": 270.0, "anode_1": 30.0, "anode_2": 150.0}
Z = Vector((0, 0, 1))


def _dir(deg):
    a = math.radians(deg)
    return Vector((math.cos(a), math.sin(a), 0.0))


def _special(name, spec, alpha=1.0, emission=0.0):
    """A spec colour that is see-through (`alpha` < 1, exported as glTF alphaMode BLEND) or
    glows (`emission`): the shared materials module has neither."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        bpy.data.materials.remove(mat)
    e = spec["materials"][name]
    col = materials.colour(e)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Metallic"].default_value = e.get("metallic", 0.0)
    bsdf.inputs["Roughness"].default_value = e.get("roughness", 0.5)
    bsdf.inputs["Alpha"].default_value = alpha
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*col, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    if alpha < 1.0:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
        if hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"
    mat.diffuse_color = (*col, alpha)
    return mat


# --- Outlines ---------------------------------------------------------------------------

def _clipped(radius, flats, n=96):
    """A circle of `radius` cut straight by `flats` {angle_deg: distance}, as points going round."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = radius
        for fa, fd in flats.items():
            c = math.cos(a - math.radians(float(fa)))
            if c > 1e-6:
                r = min(r, fd / c)
        pts.append(Vector((r * math.cos(a), r * math.sin(a), 0.0)))
    return pts


def _outline(face_d, corner_d):
    """The block's outline: an equilateral triangle (faces `face_d` from the centre) with its
    corners cut flat `corner_d` from the centre (where the mirrors sit), going round."""
    lines = [(_dir(a), face_d) for a in FACES.values()] + [(_dir(a), corner_d) for a in CORNERS.values()]
    lines.sort(key=lambda l: math.atan2(l[0].y, l[0].x))
    pts = []
    for (n1, d1), (n2, d2) in zip(lines, lines[1:] + lines[:1]):
        det = n1.x * n2.y - n1.y * n2.x
        pts.append(Vector(((d1 * n2.y - d2 * n1.y) / det, (n1.x * d2 - n2.x * d1) / det, 0.0)))
    return pts


def _ray(pts, ang):
    """Distance from the centre to the convex outline `pts` along angle `ang` (radians)."""
    u = Vector((math.cos(ang), math.sin(ang), 0.0))
    best = None
    for a, b in zip(pts, pts[1:] + pts[:1]):
        e = b - a
        det = -u.x * e.y + u.y * e.x
        if abs(det) < 1e-12:
            continue
        t = (-a.x * e.y + a.y * e.x) / det
        s = (u.x * a.y - u.y * a.x) / det
        if t > 0 and -1e-9 <= s <= 1 + 1e-9:
            best = t if best is None else min(best, t)
    return best


def _ring(ri, ro, z0, z1, e=0.0002):
    """Profile of a ring with its edges bevelled `e`, so it can be shaded smooth."""
    return [(ri + e, z0), (ro - e, z0), (ro, z0 + e), (ro, z1 - e), (ro - e, z1), (ri + e, z1), (ri, z1 - e),
            (ri, z0 + e)]


def _circle(r, n=48, centre=(0.0, 0.0)):
    return [Vector((centre[0] + r * math.cos(2 * math.pi * k / n), centre[1] + r * math.sin(2 * math.pi * k / n), 0.0))
            for k in range(n)]


def holed_plate(name, outer, holes, z0, thickness, material):
    """A flat plate: the `outer` outline with `holes` (lists of points) cut through, from z0 up
    `thickness`."""
    bm = bmesh.new()
    edges = []
    for loop in [outer] + holes:
        vs = [bm.verts.new((p.x, p.y, z0)) for p in loop]
        edges += [bm.edges.new((a, b)) for a, b in zip(vs, vs[1:] + vs[:1])]
    faces = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)["geom"]
    faces = [g for g in faces if isinstance(g, bmesh.types.BMFace)]
    ext = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(bm, vec=(0, 0, thickness),
                        verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)])
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return parts._object(name, bm, material, Matrix())


def block(name, outline, hole_r, z0, z1, material, n=96):
    """The resonator block: the outline extruded from z0 to z1 with a round hole through the
    middle (the dither motor's bore). Outline and hole are sampled at the same angles (the
    outline's corners included), so top and bottom are rings of quads."""
    angs = sorted({round(2 * math.pi * k / n, 9) for k in range(n)}
                  | {round(math.atan2(p.y, p.x) % (2 * math.pi), 9) for p in outline})
    bm = bmesh.new()
    rings = []
    for outer, z in ((True, z0), (True, z1), (False, z1), (False, z0)):
        ring = []
        for a in angs:
            r = _ray(outline, a) if outer else hole_r
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    k = len(angs)
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for i in range(k):
            j = (i + 1) % k
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return parts._object(name, bm, material, Matrix())


def _dome(radius, straight, cap, steps=6):
    """Profile of a cylinder `straight` long ending in a dome `cap` high, from the axis."""
    pts = [(0.0, 0.0), (radius, 0.0), (radius, straight)]
    for k in range(1, steps + 1):
        t = math.pi / 2 * k / steps
        pts.append((radius * math.cos(t), straight + cap * math.sin(t)))
    return pts


# --- Outside ----------------------------------------------------------------------------

def case(d, f):
    r = d["case_diameter"] / 2
    h = d["case_height"]
    cs = f["case_shape"]["value"]
    e, bd, step, lr = cs["edge"], cs["bottom_disc"], cs["bottom_step"], cs["label_radius"]
    with parts.assembly("case", core=True):
        # The side, rounded 0.5 mm at its edges (moulded; estimated), shaded smooth; the flat
        # faces are separate so they stay flat.
        parts.lathe("case_body", [(r - e, step), (r, step + e), (r, h - e), (r - e, h)], segments=96,
                    material="case_black")
        parts.lathe("case_bottom", [(0.0, 0.0), (bd, 0.0), (bd, step), (r - e, step)], segments=96,
                    material="case_black", smooth=False)
        parts.lathe("case_top", [(r - e, h), (lr, h)], segments=96, material="case_black", smooth=False)
    with parts.assembly("label"):
        parts.lathe("label", [(lr, h), (0.0, h)], segments=96, material="case_label", smooth=False)
    with parts.assembly("connector"):
        # The micro-D in an aluminium bracket at the case's top edge (sam_gg1320an
        # top_view_of_complete_rlg1.jpg); which side, and the sizes, are estimated.
        sx, sy, sz = f["connector"]["value"]["shell"]
        face = r - 0.0005
        parts.box("connector_bracket", (0.030, 0.010, 0.010), location=(0, -(face - 0.005), h - 0.0052),
                  material="aluminium")
        parts.box("connector_shell", (sx, 0.0015, sz), location=(0, -(face + 0.00075), h - 0.005),
                  material="dark_metal")


# --- Plate, housing and boards ----------------------------------------------------------

def stack(f):
    st = f["stack"]["value"]
    pl = f["plate"]["value"]
    hs = f["housing"]["value"]
    top = st["plate_bottom"] + st["plate_thickness"]
    with parts.assembly("mounting_plate", internal=True):
        holed_plate("mounting_plate", _clipped(pl["radius"], pl["flats"]), [], st["plate_bottom"],
                    st["plate_thickness"], "mid_plate_black")
        for i, (rr, ang) in enumerate(pl["screws"]):
            c = _dir(ang) * rr + Vector((0, 0, top))
            parts.cylinder(f"washer_{i + 1}", pl["screw_head"] / 2 + 0.0008, 0.0003, location=c, segments=24,
                           material="aluminium")
            parts.lathe(f"screw_{i + 1}", _dome(pl["screw_head"] / 2, 0.0003, 0.0009), location=c + Z * 0.0003,
                        segments=16, material="cathode_steel")
        for k in range(3):
            c = _dir(90 + 120 * k) * pl["hub_screws"] + Vector((0, 0, top))
            parts.lathe(f"hub_screw_{k + 1}", _dome(0.0013, 0.0003, 0.0008), location=c, segments=16,
                        material="cathode_steel")
    with parts.assembly("housing", internal=True):
        ro, w = hs["outer"], hs["wall"]
        parts.lathe("housing", _ring(ro - w, ro, top, hs["top"]), closed=True, segments=96,
                    material="aluminium")
    bp = f["pcb_parts"]["value"]
    for key in ("pcb2", "pcb1"):
        b = bp[key]
        z0 = st[key]
        t = st["pcb_thickness"]
        with parts.assembly(key, internal=True):
            o = b["outline"]
            holed_plate(key, _clipped(o["radius"], {a: o["flat"] for a in o["flats"]}), [], z0, t, "pcb_green")
            for name, (sx, sy, sz), (x, y), mat in b["parts"]:
                zc = z0 + t + sz / 2 if b["side"] > 0 else z0 - sz / 2
                parts.box(f"{key}_{name}", (sx, sy, sz), location=(x, y, zc), material=mat)
                if name in bp["leads"]["chips"]:
                    # The lead rows round the body (tinned, foil_silver stands in).
                    lr, lh = bp["leads"]["reach"], bp["leads"]["height"]
                    lz = z0 + t + lh / 2 if b["side"] > 0 else z0 - lh / 2
                    parts.box(f"{key}_{name}_leads", (sx + 2 * lr, sy + 2 * lr, lh), location=(x, y, lz),
                              material="foil_silver")
    fl = bp["flex"]
    with parts.assembly("flex_cable", internal=True):
        z0 = st["pcb2"] + st["pcb_thickness"]
        parts.box("flex_cable", (fl["width"], 0.0002, st["pcb1"] - z0), location=(0, fl["y"], (z0 + st["pcb1"]) / 2),
                  material="kapton")


# --- The laser block --------------------------------------------------------------------

def laser_block(f, spec):
    st = f["stack"]["value"]
    b = f["block"]["value"]
    pad = f["pad"]["value"]
    zb = st["plate_bottom"] - pad["thickness"]
    z0 = zb - b["thickness"]
    zc = z0 + b["thickness"] / 2
    R = b["corner_cut"]  # the beam turns on the mirror faces, which sit on the corner flats
    inr = R / 2  # the bores' distance from the centre (an equilateral triangle's inradius)
    glass = _special("block_glass", spec, alpha=0.22)
    corners = [_dir(a) * R + Vector((0, 0, zc)) for a in CORNERS.values()]
    sides = list(zip(corners, corners[1:] + corners[:1]))
    with parts.assembly("resonator_block", internal=True):
        block("resonator_block", _outline(b["face_distance"], b["corner_cut"]), b["centre_bore"] / 2,
              z0, zb, glass)
        # The three beam bores and the discharge channels, as glass tubes so their walls show.
        br = f["bores"]["value"]["diameter"] / 2
        for i, (p, q) in enumerate(sides):
            parts.cylinder(f"bore_{i + 1}", br, (q - p).length, location=p, direction=q - p, segments=12,
                           material=glass, caps=False)
        dc = f["discharge_channels"]["value"]
        face = b["face_distance"]
        for key, ang in FACES.items():
            u = _dir(ang)
            side = _dir(ang + 90)
            offs = (-dc["cathode_spacing"] / 2, dc["cathode_spacing"] / 2) if key == "cathode" else (0.0,)
            for j, o in enumerate(offs):
                p = u * face + side * o + Vector((0, 0, zc))
                parts.cylinder(f"{key}_channel_{j + 1}", dc["diameter"] / 2, face - inr + br, location=p,
                               direction=-u, segments=10, material=glass, caps=False)
        cw = f["corner_wells"]["value"]
        for key, ang in CORNERS.items():
            u = _dir(ang)
            parts.cylinder(f"{key}_well", cw["diameter"] / 2, R - cw["inner_end"],
                           location=u * cw["inner_end"] + Vector((0, 0, zc)), direction=u, segments=24,
                           material=glass)
    with parts.assembly("pad", internal=True):
        outer = _outline(b["face_distance"] - pad["inset"], b["corner_cut"] - pad["inset"])
        outer = [Vector((_ray(outer, a) * math.cos(a), _ray(outer, a) * math.sin(a), 0))
                 for a in [2 * math.pi * k / 96 for k in range(96)]]
        holes = [_circle(pad["centre_hole"] / 2)]
        for ang in CORNERS.values():
            holes.append([_dir(ang) * pad["window_outer"], _dir(ang + pad["window_half_angle"]) * pad["window_inner"],
                          _dir(ang - pad["window_half_angle"]) * pad["window_inner"]])
        holed_plate("pad", outer, holes, zb, pad["thickness"], "pad_lattice")
    beam = _special("laser_beam", spec, emission=3.0)
    with parts.assembly("laser_path", internal=True):
        for i, (p, q) in enumerate(sides):
            parts.cylinder(f"beam_{i + 1}", 0.0003, (q - p).length, location=p, direction=q - p, segments=8,
                           material=beam)
    return z0, zb, zc, R


def mirrors(f, zc, R):
    m = f["mirrors"]["value"]
    dt = f["detector"]["value"]
    ends = {}
    for key, ang in CORNERS.items():
        u = _dir(ang)
        p = u * R + Vector((0, 0, zc))
        with parts.assembly(key, internal=True):
            parts.cylinder(f"{key}_substrate", m["diameter"] / 2, m["substrate"], location=p, direction=u,
                           segments=32, material="foil_silver")
            q = p + u * m["substrate"]
            if key == "mirror_2":
                # The detector, potted in grey rubber on the wedged substrate, with its two
                # photodiode packages and their pins (u is +Y here).
                parts.lathe(f"{key}_potting", _dome(dt["potting_radius"], 0.0005, dt["potting_height"] - 0.0005),
                            location=q, direction=u, segments=32, material="rtv_grey")
                sx, sy, sz = dt["photodiode_size"]
                for i, (x, out) in enumerate(dt["photodiodes"]):
                    c = Vector((x, q.y + out, zc + 0.0006))
                    parts.box(f"photodiode_{i + 1}", (sx, sy, sz), location=c, material="photodiode_package")
                    for k in range(dt["pins"]):
                        px = x + (k - (dt["pins"] - 1) / 2) * sx * 0.3
                        parts.cylinder(f"photodiode_{i + 1}_pin_{k + 1}", 0.0002, dt["pin_length"],
                                       location=(px, c.y, c.z - sz / 2 + 0.0002), direction=(0, 0, -1),
                                       segments=6, material="gold_pin")
                x0, out0 = dt["photodiodes"][0]
                parts.lathe(f"{key}_epoxy", _dome(0.002, 0.0, 0.0012), location=(x0 - 0.0004, q.y + out0 + sy / 2 - 0.0003, zc),
                            direction=u, segments=16, material="amber_epoxy")
                ends[key] = q + u * dt["potting_height"]
            else:
                parts.cylinder(f"{key}_pzt", m["pzt"] / 2, m["pzt"], location=q, direction=u, segments=32,
                               material="pzt_ceramic")
                ends[key] = q + u * m["pzt"]
    return ends


def discharge(f, zc):
    face = f["block"]["value"]["face_distance"]
    dc = f["discharge"]["value"]
    cf = f["cathode_flange"]["value"]
    tips = {}
    for key, ang in FACES.items():
        u = _dir(ang)
        p = u * face + Vector((0, 0, zc))
        with parts.assembly(key, internal=True):
            if key == "cathode":
                cr = dc["cathode_diameter"] / 2
                parts.cylinder("cathode_flange", cf["diameter"] / 2, cf["thickness"], location=p, direction=u,
                               segments=48, material="cathode_steel")
                parts.cylinder("cathode_seal", cf["seal_diameter"] / 2, cf["seal_thickness"],
                               location=p + u * cf["thickness"], direction=u, segments=48, material="gold_seal")
                body = dc["cathode_length"] - cf["thickness"]
                parts.lathe("cathode", _dome(cr, body - cr, cr), location=p + u * cf["thickness"], direction=u,
                            segments=48, material="cathode_steel")
                tx, ty, tz = cf["tab"]
                tab = p + u * (cf["thickness"] + tz / 2) + Vector((0, 0, cr + ty / 2))
                # u is -Y: the tab stands along the cathode, lying on its top.
                parts.box("cathode_tab", (tx, tz, ty), location=tab, material="gold_seal")
                tips[key] = tab
            elif key == "anode_2":
                parts.lathe(key, _dome(dc["anode_diameter"] / 2, 0.0, dc["anode_height"]), location=p, direction=u,
                            segments=32, material="cathode_steel")
                cx, cy, cz = f["anode_2_cover"]["value"]
                parts.box("anode_2_cover", (cz, cx, cy), location=p + u * (cz / 2), roll_deg=ang,
                          material="anode_cover_red")
                tips[key] = p + u * cz
            else:
                parts.lathe(key, _dome(dc["anode_diameter"] / 2, 0.0, dc["anode_height"]), location=p,
                            direction=u, segments=32, material="cathode_steel")
                tips[key] = p + u * dc["anode_height"]
    return tips


def dither(f, z0, zb, zp):
    dv = f["dither"]["value"]
    h = zb - z0
    zm = (z0 + zb) / 2
    ro = dv["ring_diameter"] / 2
    ri = ro - 0.0012
    rh = dv["hub_diameter"] / 2
    with parts.assembly("dither_motor", internal=True):
        parts.lathe("dither_ring", _ring(ri, ro, z0, zb), closed=True, segments=64, material="dither_wheel")
        # The hub runs up to the plate: the block hangs from it.
        parts.cylinder("dither_hub", rh, zp - z0, location=(0, 0, z0), segments=32, material="dither_wheel")
        for k in range(dv["spokes"]):
            deg = 90.0 + 120.0 * k
            L = ri - rh + 0.0004
            c = _dir(deg) * (rh - 0.0002 + L / 2)
            parts.box(f"dither_spoke_{k + 1}", (L, 0.0012, h * 0.8), location=(c.x, c.y, zm), roll_deg=deg,
                      material="dither_wheel")
            # A piezo plate on each side of the spoke: the motor's drive (estimated sizes).
            n = _dir(deg + 90.0)
            for s, tag in ((-1, "a"), (1, "b")):
                pc = c + n * (s * 0.0009)
                parts.box(f"dither_pzt_{k + 1}{tag}", (L * 0.6, 0.0006, h * 0.6), location=(pc.x, pc.y, zm),
                          roll_deg=deg, material="pzt_ceramic")


def extras(f, zc, ends, tips):
    g = f["getter"]["value"]
    face = f["block"]["value"]["face_distance"]
    with parts.assembly("getter", internal=True):
        # On the block's bottom face (sam_gg1320an's "Getter" label), length estimated.
        parts.cylinder("getter", g["diameter"] / 2, 0.003, location=(g["position"][0], -face, zc),
                       direction=(0, -1, 0), segments=24, material="foil_silver")
    cb = f["connector_bars"]["value"]
    bars = {}
    with parts.assembly("connector_bars", internal=True):
        for key, ang in (("bc1", 150.0), ("bc2", 30.0)):
            c = _dir(ang) * cb["distance"] + Vector((0, 0, zc))
            t = _dir(ang + 90) * (cb["length"] / 2 - 0.002)
            bars[key] = (c, c + t, c - t)  # middle, then the ends nearer +t and -t
            parts.box(key, (cb["width"], cb["length"], cb["height"]), location=c, roll_deg=ang,
                      material="connector_white")
    # Wires from the bars to the parts they feed: a red and a white strand each, routed
    # simplified (facts.wires).
    rw = f["wires"]["value"]["radius"]
    runs = [("bc1", 0, "anode_2"), ("bc1", 1, "mirror_1"), ("bc1", 2, "mirror_2"),
            ("bc2", 0, "anode_1"), ("bc2", 1, "mirror_2"), ("bc2", 2, "mirror_3"), ("bc2", 2, "cathode")]
    targets = {**ends, **tips}
    with parts.assembly("wiring", internal=True):
        for i, (bar, end, target) in enumerate(runs):
            a = bars[bar][end]
            b = targets[target]
            if target in ends:
                # Join a mirror at its rim on the bar's side, not across its face.
                u = _dir(CORNERS[target])
                side = (a - b) - u * (a - b).dot(u)
                side.z = 0
                b = b - u * 0.001 + side.normalized() * (f["mirrors"]["value"]["diameter"] / 2)
            out = (b.to_2d().normalized() * (b.to_2d().length + 0.003)).to_3d()
            mid = (a + out) / 2
            mid = (mid.to_2d().normalized() * max(mid.to_2d().length, 0.031)).to_3d()
            if target == "cathode":
                mid = _dir(300) * 0.033
            for k, (dz, mat) in enumerate(((0.0004, "wire_red"), (-0.0004, "wire_white"))):
                lift = Vector((0, 0, zc + 0.0025 + dz))
                pts = [a + Vector((0, 0, cb["height"] / 2 + dz + 0.0004)), mid + lift, out + lift,
                       b + Vector((0, 0, dz))]
                parts.tube(f"wire_{i + 1}{'ab'[k]}", pts, rw, segments=6, bend_radius=0.002, material=mat)


def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    f = spec["facts"]
    case(d, f)
    stack(f)
    z0, zb, zc, R = laser_block(f, spec)
    ends = mirrors(f, zc, R)
    tips = discharge(f, zc)
    dither(f, z0, zb, f["stack"]["value"]["plate_bottom"])
    extras(f, zc, ends, tips)
