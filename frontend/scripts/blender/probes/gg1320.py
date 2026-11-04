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


def case(d, f):
    r = d["case_diameter"] / 2
    h = d["case_height"]
    with parts.assembly("case", core=True):
        # Edges rounded 0.5 mm (moulded; estimated), so the side shades smooth.
        e = 0.0005
        parts.lathe("case_body", [(0.0, 0.0), (r - 2 * e, 0.0), (r - e, 0.0), (r, e), (r, h - e), (r - e, h),
                                 (r - 2 * e, h), (0.0, h)],
                    segments=96, material="case_black")
    with parts.assembly("connector"):
        # The micro-D in an aluminium bracket cut into the case's top edge (sam_gg1320an
        # top_view_of_complete_rlg1.jpg); which side, and the sizes, are estimated.
        sx, sy, sz = f["connector"]["value"]["shell"]
        face = r - 0.0005
        parts.box("connector_bracket", (0.030, 0.010, 0.010), location=(0, -(face - 0.005), h - 0.0052),
                  material="foil_silver")
        parts.box("connector_shell", (sx, 0.0015, sz), location=(0, -(face + 0.00075), h - 0.005),
                  material="dark_metal")


def stack(d, f):
    st = f["stack"]["value"]
    r = d["case_diameter"] / 2 - st["wall"] - 0.0005
    with parts.assembly("mounting_plate", internal=True):
        parts.cylinder("mounting_plate", r, st["plate_thickness"], location=(0, 0, st["plate_bottom"]),
                       segments=96, material="mid_plate_black")
    for key in ("pcb2", "pcb1"):
        with parts.assembly(key, internal=True):
            parts.cylinder(key, r - 0.001, st["pcb_thickness"], location=(0, 0, st[key]), segments=96,
                           material="pcb_green")


def laser_block(f, spec):
    st = f["stack"]["value"]
    b = f["block"]["value"]
    z0 = st["plate_bottom"] - b["thickness"]
    zc = z0 + b["thickness"] / 2
    R = b["corner_cut"]  # the beam turns on the mirror faces, which sit on the corner flats
    glass = _special("block_glass", spec, alpha=0.22)
    corners = [_dir(a) * R + Vector((0, 0, zc)) for a in CORNERS.values()]
    sides = list(zip(corners, corners[1:] + corners[:1]))
    with parts.assembly("resonator_block", internal=True):
        block("resonator_block", _outline(b["face_distance"], b["corner_cut"]), b["centre_bore"] / 2,
              z0, z0 + b["thickness"], glass)
        # The three bores, as open glass tubes so their walls show through the block.
        br = f["bores"]["value"]["diameter"] / 2
        for i, (p, q) in enumerate(sides):
            parts.cylinder(f"bore_{i + 1}", br, (q - p).length, location=p, direction=q - p, segments=12,
                           material=glass, caps=False)
    beam = _special("laser_beam", spec, emission=3.0)
    with parts.assembly("laser_path", internal=True):
        for i, (p, q) in enumerate(sides):
            parts.cylinder(f"beam_{i + 1}", 0.0003, (q - p).length, location=p, direction=q - p, segments=8,
                           material=beam)
    return z0, zc, R


def mirrors(f, zc, R):
    m = f["mirrors"]["value"]
    for key, ang in CORNERS.items():
        u = _dir(ang)
        p = u * R + Vector((0, 0, zc))
        with parts.assembly(key, internal=True):
            parts.cylinder(f"{key}_substrate", m["diameter"] / 2, m["substrate"], location=p, direction=u,
                           segments=32, material="foil_silver")
            q = p + u * m["substrate"]
            if key == "mirror_2":
                # The detector assembly on the wedged substrate (readout prism and photodiodes).
                dx, dy, dz = m["detector_block"]
                parts.box(f"{key}_detector", (dx, dz, dy), location=q + u * (dz / 2), material="dark_metal")
            else:
                parts.cylinder(f"{key}_pzt", m["pzt"] / 2, m["pzt"], location=q, direction=u, segments=32,
                               material="pzt_ceramic")


def _dome(radius, straight, cap, steps=6):
    """Profile of a cylinder `straight` long ending in a dome `cap` high, from the axis."""
    pts = [(0.0, 0.0), (radius, 0.0), (radius, straight)]
    for k in range(1, steps + 1):
        t = math.pi / 2 * k / steps
        pts.append((radius * math.cos(t), straight + cap * math.sin(t)))
    return pts


def discharge(f, zc):
    face = f["block"]["value"]["face_distance"]
    dc = f["discharge"]["value"]
    for key, ang in FACES.items():
        u = _dir(ang)
        p = u * face + Vector((0, 0, zc))
        with parts.assembly(key, internal=True):
            if key == "cathode":
                cr = dc["cathode_diameter"] / 2
                parts.lathe("cathode", _dome(cr, dc["cathode_length"] - cr, cr), location=p, direction=u,
                            segments=48, material="cathode_steel")
            else:
                mat = "anode_cover_red" if key == "anode_2" else "cathode_steel"
                parts.lathe(key, _dome(dc["anode_diameter"] / 2, 0.0, dc["anode_height"]), location=p,
                            direction=u, segments=32, material=mat)


def dither(f, z0, z1):
    dv = f["dither"]["value"]
    h = z1 - z0
    zm = (z0 + z1) / 2
    ro = dv["ring_diameter"] / 2
    ri = ro - 0.0012
    rh = dv["hub_diameter"] / 2
    with parts.assembly("dither_motor", internal=True):
        parts.lathe("dither_ring", [(ri, z0), (ro, z0), (ro, z1), (ri, z1)], closed=True, segments=64,
                    material="dither_wheel", smooth=False)
        parts.cylinder("dither_hub", rh, h, location=(0, 0, z0), segments=32, material="dither_wheel")
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


def extras(f, zc):
    g = f["getter"]["value"]
    face = f["block"]["value"]["face_distance"]
    with parts.assembly("getter", internal=True):
        # On the block's bottom face (sam_gg1320an's "Getter" label), length estimated.
        parts.cylinder("getter", g["diameter"] / 2, 0.003, location=(g["position"][0], -face, zc),
                       direction=(0, -1, 0), segments=24, material="foil_silver")
    cb = f["connector_bars"]["value"]
    with parts.assembly("connector_bars", internal=True):
        for key, ang in (("bc1", 150.0), ("bc2", 30.0)):
            c = _dir(ang) * cb["distance"] + Vector((0, 0, zc))
            parts.box(key, (cb["width"], cb["length"], cb["height"]), location=c, roll_deg=ang,
                      material="connector_white")


def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    f = spec["facts"]
    case(d, f)
    stack(d, f)
    z0, zc, R = laser_block(f, spec)
    z1 = f["stack"]["value"]["plate_bottom"]
    mirrors(f, zc, R)
    discharge(f, zc)
    dither(f, z0, z1)
    extras(f, zc)
