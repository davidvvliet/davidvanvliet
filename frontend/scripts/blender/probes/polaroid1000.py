# Polaroid Land Camera 1000 (Supercolor 1000). Built from lib/parts in metres; every number comes
# from specs/polaroid1000.json (with its source) or is marked here as estimated.
# Frame while building: z up, bottom at z = 0, centred; the lens along +y, +x the button side (the
# spec's frame). build() turns the result 180 degrees about z: the model faces -y.
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

import numpy as np

from lib import materials, parts, tiling

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "refs", "polaroid1000")
HALF_W = 0.0535  # half the 107 mm width
SEAM = 0.0005  # the film door's gap, estimated from halicki_2023 (2)


# --- shape helpers ------------------------------------------------------------------------

def _solid(name, verts, faces, material):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    return parts._object(name, bm, material, Matrix(), None)


def side_prism(name, poly, x0, x1, material):
    """A solid from a side outline [(y, z), ...] swept across x0..x1."""
    n = len(poly)
    verts = [(x0, y, z) for y, z in poly] + [(x1, y, z) for y, z in poly]
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return _solid(name, verts, faces, material)


def ccyl(name, radius, length, location, direction=(0, 0, 1), **kw):
    """parts.cylinder centred on `location` (parts.cylinder starts there)."""
    d = Vector(direction).normalized()
    return parts.cylinder(name, radius, length, location=tuple(Vector(location) - d * length / 2),
                          direction=direction, **kw)


def circle(r, n=40):
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rrect(w, h, r, n=5):
    """Rounded rectangle (u, v) points, counter-clockwise, centred."""
    pts = []
    for cu, cv, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def front_ring(name, outer, inner, cx, cz, y0, y1, material, inner_y0=None):
    """A frame facing +y (outer and inner outlines with the same point count) from y0 to y1;
    the hole's wall runs back to `inner_y0` (default y0)."""
    n = len(outer)
    iy = y0 if inner_y0 is None else inner_y0
    P = lambda uv, y: (cx + uv[0], y, cz + uv[1])
    verts = [P(p, y1) for p in outer] + [P(p, y1) for p in inner] + \
            [P(p, y0) for p in outer] + [P(p, iy) for p in inner]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        faces.append((2 * n + i, 2 * n + j, j, i))
        faces.append((n + i, n + j, 3 * n + j, 3 * n + i))
        faces.append((3 * n + i, 3 * n + j, 2 * n + j, 2 * n + i))
    return _solid(name, verts, faces, material)


def front_plate(name, outline, cx, cz, y0, y1, material):
    """A solid from a front outline [(u, v)] (u along x, v along z), y0..y1."""
    n = len(outline)
    verts = [(cx + u, y1, cz + v) for u, v in outline] + [(cx + u, y0, cz + v) for u, v in outline]
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return _solid(name, verts, faces, material)


def domed_plate(name, outline, cx, cz, y0, t, dome, material, rings=5):
    """A plate from a front outline, `t` thick from y0, its front bulging forward by `dome`."""
    n = len(outline)
    layers = [(1.0, y0), (1.0, y0 + t)]
    for i in range(1, rings):
        a = (math.pi / 2) * i / rings
        layers.append((math.cos(a), y0 + t + dome * math.sin(a)))
    verts = [(cx + u * k, y, cz + v * k) for k, y in layers for u, v in outline]
    verts.append((cx, y0 + t + dome, cz))
    faces = [list(range(n - 1, -1, -1))]
    for L in range(len(layers) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((L * n + i, L * n + j, (L + 1) * n + j, (L + 1) * n + i))
    top, c = (len(layers) - 1) * n, len(verts) - 1
    faces += [(top + i, top + (i + 1) % n, c) for i in range(n)]
    return _solid(name, verts, faces, material)


def slab(name, corners, normal, t, material):
    """A thin plate on four world corners, thickness t along `normal`."""
    nv = Vector(normal).normalized() * t
    a = [Vector(c) for c in corners]
    verts = [tuple(v) for v in a] + [tuple(v + nv) for v in a]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return _solid(name, verts, faces, material)


def _apply(obj):
    """Bake an object's modifiers into its mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear()
    old = obj.data
    obj.data = me
    bpy.data.meshes.remove(old)


def fuse(name, objs):
    """One moulding from several closed solids (exact boolean union); keeps the first's tags."""
    base = objs[0]
    for o in objs[1:]:
        m = base.modifiers.new("union", "BOOLEAN")
        m.operation, m.solver, m.object = "UNION", "EXACT", o
        m.material_mode = "TRANSFER"
    _apply(base)
    for o in objs[1:]:
        bpy.data.objects.remove(o)
    base.name = base.data.name = name
    return base


def cut(obj, size, location):
    """Cut a box out of an object (exact boolean difference)."""
    box = parts.box(obj.name + "_cut", size, location=location, material=obj.data.materials[0].name)  # the cut's walls take the object's finish
    m = obj.modifiers.new("cut", "BOOLEAN")
    m.operation, m.solver, m.object = "DIFFERENCE", "EXACT", box
    _apply(obj)
    bpy.data.objects.remove(box)
    return obj


def hull(name, points, material):
    """The convex hull of a set of points, as a closed solid."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.delete(bm, geom=[v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return parts._object(name, bm, material, Matrix(), None)


def _apply_transform(obj):
    obj.data.transform(obj.matrix_basis)
    obj.matrix_basis = Matrix()


def round_edges(obj, width, segments=4, angle=30, clamp=True):
    """Round every edge sharper than `angle` degrees (moulded plastic), concave ones filleted.
    The mesh is tidied first: a boolean leaves split faces and sliver edges, and the bevel's
    overlap clamp would shrink the rounding to the shortest of them."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts, edges=bm.edges)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
    bm.to_mesh(obj.data)
    bm.free()
    m = obj.modifiers.new("round", "BEVEL")
    m.width, m.segments, m.limit_method = width, segments, "ANGLE"
    m.angle_limit = math.radians(angle)
    m.use_clamp_overlap = clamp
    _apply(obj)
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(35))
    return obj


def gear(name, radius, width, centre, material, module=0.0005):
    """A spur gear on the x axis: teeth about two modules deep, one per 3.14 modules of rim."""
    teeth = max(8, int(2 * radius / module))
    pts = []
    for k in range(teeth):
        for f, r in ((0.0, radius - module), (0.2, radius + module * 0.8), (0.5, radius + module * 0.8), (0.7, radius - module)):
            a = 2 * math.pi * (k + f) / teeth
            pts.append((r * math.cos(a), r * math.sin(a)))
    n = len(pts)
    cx, cy, cz = centre
    verts = [(cx + width / 2, cy + u, cz + v) for u, v in pts] + [(cx - width / 2, cy + u, cz + v) for u, v in pts]
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return _solid(name, verts, faces, material)


def glow(key, spec, alpha, emission):
    """A see-through, faintly glowing version of spec material `key` (the light bundle)."""
    e = spec["materials"][key]
    col = materials.colour(e)
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = e.get("roughness", 0.5)
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Emission Color"].default_value = (*col, 1.0)
    bsdf.inputs["Emission Strength"].default_value = emission
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    mat.diffuse_color = (*col, alpha)
    return mat


def _image_material(name, file, roughness=0.5):
    img = bpy.data.images.load(os.path.join(REFS, file), check_existing=True)
    return materials.image(name, img, metallic=0.0, roughness=roughness)


def _scene_material():
    """The viewfinder's view (refs viewfinder-scene.jpg), glowing at half strength."""
    mat = _image_material("viewfinder_scene", "viewfinder-scene.jpg", 0.6)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 0.5
    return mat


def _uv_plane(obj, axis_u, axis_v, u0, u1, v0, v1):
    """Planar UVs: world axis_u from u0 to u1 and axis_v from v0 to v1 map to [0, 1]."""
    me = obj.data
    uv = me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name="UVMap")
    M = obj.matrix_world
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = M @ me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co[axis_u] - u0) / (u1 - u0), (co[axis_v] - v0) / (v1 - v0))


# --- outside ------------------------------------------------------------------------------

def shell(P):
    door, low, fs = P["door"], P["lower_box"], P["front_section"]
    plate, shelf, wb = P["front_plate"], P["shelf_front"], P["white_cover_back"]
    with parts.assembly("body", core=True):
        # One moulding, built from simple pieces each rounded on its own (a single bevel over the
        # joined body gets capped by its shortest edges), then joined; where two pieces meet, the
        # rounded edge of one is buried in the other.
        # The lower box and the front frame: one L-shaped profile. The box runs on under the door,
        # so its rounding stops short of the seam cut below.
        frame = side_prism("lower_frame", [(low["y0"], 0.0), (door["y0"] + 0.004, 0.0), (door["y0"] + 0.004, low["height"]),
                                           (wb, low["height"]), (wb, fs["top"]), (fs["y0"], fs["top"]),
                                           (fs["y0"], low["height"]), (low["y0"], low["height"])], -HALF_W, HALF_W, "body_black")
        round_edges(frame, P["rounding"]["body"])
        # The pyramid over the mirror: its back slopes down to the rear wall and its sides lean
        # in (7 mm inset at the top, estimated from halicki_2023 (1) and (2)); its foot and front
        # run on into the box and frame, so only its free edges show rounded.
        z0, z1, y0, y1, inset = low["height"], fs["top"], low["y0"], fs["y0"], 0.007
        b = P["back"]["base_inset"]          # a ledge along the lower box's sides at the foot
        zd, yd = z0 - 0.006, y1 + 0.006
        verts = [(HALF_W - b, y0, zd), (-HALF_W + b, y0, zd), (-HALF_W + b, yd, zd), (HALF_W - b, yd, zd),
                 (HALF_W - b, y0, z0), (-HALF_W + b, y0, z0),
                 (HALF_W - inset, y1, z1 - 0.001), (-HALF_W + inset, y1, z1 - 0.001),
                 (HALF_W - inset, yd, z1 - 0.001), (-HALF_W + inset, yd, z1 - 0.001)]    # just under the frame's top
        # Matte and grained like the hood; the rest of the moulding is glossy (halicki_2023 (2)).
        pyr = hull("pyramid", verts, "hood_matte")
        round_edges(pyr, P["rounding"]["back"])
        hood = viewfinder_hood(P)
        round_edges(hood, P["rounding"]["hood"])
        shell_obj = fuse("body_shell", [frame, pyr, hood])
        shell_obj.data.shade_smooth()
        shell_obj.data.set_sharp_from_angle(angle=math.radians(35))
        # The strap's two slots at the top of the rear face.
        sl = P["back"]["strap_slot"]
        for sx in (1, -1):
            cut(shell_obj, (sl["w"], 2 * sl["depth"], sl["h"]), (sx * sl["x"], low["y0"], sl["z"]))
        # The film door's seam: a fine square-edged gap on the sides and bottom (halicki_2023 (2)).
        cut(shell_obj, (0.2, 0.1, door["height"] + 0.01), (0, door["y0"] - SEAM / 2 + 0.05, (door["height"] - 0.0101) / 2))
        # Strap lugs: a small rounded bar on each side of the front frame, near the top.
        for sgn in (1, -1):
            lug = parts.box(f"strap_lug_{'p' if sgn > 0 else 'm'}", (0.004, 0.009, 0.0028),
                            location=(sgn * (HALF_W + 0.001), wb - 0.007, fs["top"] - 0.008), material="body_black")
            round_edges(lug, 0.001, segments=3)
    with parts.assembly("film_door"):
        dz, dy0, dy1 = door["height"], door["y0"], door["y1"]
        slot = P["exit_slot"]
        hw = slot["half_width"]
        # One rounded block, the exit slot cut into its face.
        door_obj = side_prism("door", [(dy0 - 0.004, 0.0), (dy1, 0.0), (dy1, dz), (dy0 - 0.004, dz)],
                              -HALF_W + 0.0002, HALF_W - 0.0002, "body_black")
        round_edges(door_obj, P["rounding"]["door"])
        cut(door_obj, (2 * hw, 0.012, slot["z1"] - slot["z0"]), (0, dy1, (slot["z0"] + slot["z1"]) / 2))
        round_edges(door_obj, 0.0006, segments=2, angle=60)
        cut(door_obj, (0.2, 0.1, 0.1), (0, door["y0"] + SEAM / 2 - 0.05, 0))
        # The seam's floor: dark, just inside the outer faces.
        parts.box("door_seam", (2 * HALF_W - 0.0012, SEAM, dz - 0.0008), location=(0, dy0, dz / 2 + 0.0002),
                  material="lightbox_black")
        strip = parts.box("name_strip", (0.101, 0.0008, slot["label_z1"] - slot["label_z0"]),
                          location=(0, dy1 + 0.0004, (slot["label_z0"] + slot["label_z1"]) / 2),
                          material=_image_material("name_strip", "name-strip.jpg", 0.4))
        # The photo runs left to right as seen from the front, so +x is its left edge.
        _uv_plane(strip, 0, 2, 0.0505, -0.0505, slot["label_z0"], slot["label_z1"])
    with parts.assembly("door_latch"):
        # On the body just behind the seam: ribs on the rear part, an arrow pointing forward.
        la = P["door_latch"]
        y0, y1, z0, z1, d = la["y0"], la["y1"], la["z0"], la["z1"], la["depth"]
        latch = parts.box("latch", (d, y1 - y0, z1 - z0), location=(HALF_W + d / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                          material="body_black")
        round_edges(latch, 0.0004, segments=2)
        x = HALF_W + d
        n, pitch = 7, 0.0011
        parts.boxes("latch_ribs", [((0.0003, 0.0005, z1 - z0 - 0.0014), (x + 0.0001, y0 + 0.0012 + k * pitch, (z0 + z1) / 2))
                                   for k in range(n)], material="body_black")
        zc, ya = (z0 + z1) / 2, y0 + 0.0012 + n * pitch + 0.0008
        side_prism("latch_arrow", [(ya, zc - 0.0016), (ya + 0.0020, zc - 0.0016), (ya + 0.0036, zc), (ya + 0.0020, zc + 0.0016),
                                   (ya, zc + 0.0016)], x - 0.0001, x + 0.00025, "body_black")
    with parts.assembly("front_cover"):
        # White right up to the top edge, rounded over it; the black deck starts behind it.
        cover = side_prism("white_cover", [(wb, shelf["z"]), (shelf["y"], shelf["z"]),
                                           (plate["y"], plate["bottom"]), (plate["y"], fs["top"]), (wb, fs["top"])],
                           -HALF_W, HALF_W, "front_white")
        round_edges(cover, P["rounding"]["front"])
        # The lens sits behind the hood's back window, its top hidden by the window's edge
        # (halicki_2023 (3)): a pocket in the cover for it.
        lp = lens_pocket(P)
        cut(cover, (lp["w"], lp["y1"] - lp["y0"] + 0.001, lp["z1"] - lp["z0"]),
            (lp["x"], (lp["y0"] + lp["y1"] + 0.001) / 2, (lp["z0"] + lp["z1"]) / 2))
    stripe(P)


def stripe(P):
    """Five bands from under the lens boss down the front plate and the shelf to its front edge, magenta on +x."""
    s, plate, shelf = P["stripe"], P["front_plate"], P["shelf_front"]
    w = s["width"] / s["bands"]
    a = Vector((0, plate["y"], plate["bottom"]))
    b = Vector((0, shelf["y"], shelf["z"]))
    d = b - a
    nrm = Vector((0, -d.z, d.y)).normalized()
    if nrm.z < 0:
        nrm = -nrm
    with parts.assembly("stripe"):
        for k, m in enumerate(["stripe_magenta", "stripe_orange", "stripe_yellow", "stripe_green", "stripe_blue"]):
            x0 = s["width"] / 2 - k * w
            x1 = x0 - w
            slab(m, [(x0, a.y, a.z), (x1, a.y, a.z), (x1, b.y, b.z), (x0, b.y, b.z)], nrm, 0.0002, m)
            # ... and a short run down the front plate, from under the lens boss to the shelf.
            zb = P["lens_boss"]["z"] - P["lens_boss"]["height"] / 2 + 0.001
            slab(m + "_plate", [(x0, a.y, zb), (x1, a.y, zb), (x1, a.y, a.z), (x0, a.y, a.z)], Vector((0, 1, 0)), 0.0002, m)


def lens_pocket(P):
    """The space behind the hood's back window that holds the lens: the window's width, from just
    below the window to above it and the lens cell, 6 mm deep behind the front plate."""
    lb, py = P["lens_boss"], P["front_plate"]["y"]
    return {"x": lb["x"], "w": lb["lens_frame"], "y0": py - 0.006, "y1": py,
            "z0": lb["lens_frame_z"] - lb["lens_frame"] / 2 - 0.001,
            "z1": max(P["lens_centre_z"] + 0.0085, lb["lens_frame_z"] + lb["lens_frame"] / 2 + 0.001)}


def front_parts(P):
    py = P["front_plate"]["y"]
    lb = P["lens_boss"]
    with parts.assembly("lens_boss"):
        ow, oh, oz = lb["opening_w"], lb["opening_h"], lb["opening_z"]
        # The white frame (its hole off-centre: the top border is the widest) ...
        outer = [(u, v + lb["z"] - oz) for u, v in rrect(lb["width"], lb["height"], 0.007)]
        boss = front_ring("boss", outer, rrect(ow, oh, 0.005), lb["x"], oz, py - 0.001, py + lb["depth"], "front_white",
                          inner_y0=py + lb["depth"] - 0.0015)
        round_edges(boss, 0.0015, segments=3, angle=40)
        # ... and inside it the black stepped hood, narrowing back to the lens frame.
        steps = lb["steps"]
        y = py + lb["depth"] - 0.0015
        dy = (y - py - 0.0005) / steps
        for k in range(steps):
            f0, f1 = k / steps, (k + 1) / steps
            w0, w1 = ow + (lb["lens_frame"] - ow) * f0, ow + (lb["lens_frame"] - ow) * f1
            h0, h1 = oh + (lb["lens_frame"] - oh) * f0, oh + (lb["lens_frame"] - oh) * f1
            zc = oz + (lb["lens_frame_z"] - oz) * f1
            front_ring(f"hood_step_{k}", [(u, v + (oz + (lb["lens_frame_z"] - oz) * f0) - zc) for u, v in rrect(w0, h0, 0.004)],
                       rrect(w1, h1, 0.0035), lb["x"], zc, y - dy, y, "body_black")
            # No edge rounding: along the top a step is only ~0.26 mm deep and a bevel folds it.
            y -= dy
        # The pocket behind the window, lined black.
        lp = lens_pocket(P)
        pw, ph, pz = lp["w"], lp["z1"] - lp["z0"], (lp["z0"] + lp["z1"]) / 2
        front_ring("hood_back", rrect(pw + 0.001, ph + 0.001, 0.002), rrect(pw - 0.0005, ph - 0.0005, 0.0015), lp["x"], pz,
                   lp["y0"], py + 0.0005, "body_black")
        front_plate("hood_back_wall", rrect(pw, ph, 0.002), lp["x"], pz, lp["y0"], lp["y0"] + 0.0005, "body_black")
    with parts.assembly("lens"):
        # The single 103 mm element: domed, rounded-square, filling the window; the shutter's round
        # opening shows through it.
        cg = P["lens_dome"]
        glass = domed_plate("lens_element", rrect(cg["width"], cg["height"], cg["radius"]), lb["x"], cg["z"], py - 0.0004,
                            0.0004, cg["dome"], glow("lens_dome", SPEC[0], SPEC[0]["materials"]["lens_dome"]["alpha"], 0.0))
        glass.data.shade_smooth()
    with parts.assembly("viewfinder_window"):
        vw = P["viewfinder_window"]
        wf = front_ring("window_frame", rrect(vw["width"] + 0.003, vw["height"] + 0.003, 0.0015),
                   rrect(vw["width"], vw["height"], 0.001), vw["x"], vw["z"], py, py + 0.0015, "front_white")
        round_edges(wf, 0.0004, segments=2)
        glass = front_plate("window_glass", rrect(vw["width"], vw["height"], 0.001), vw["x"], vw["z"],
                            py, py + 0.0005, _image_material("viewfinder_glass", "viewfinder.jpg", 0.05))
        _uv_plane(glass, 0, 2, vw["x"] + vw["width"] / 2, vw["x"] - vw["width"] / 2,
                  vw["z"] - vw["height"] / 2, vw["z"] + vw["height"] / 2)
    with parts.assembly("shutter_button"):
        b = P["button"]
        round_edges(front_plate("button_bezel", circle(b["bezel"] / 2), b["x"], b["z"], py, py + 0.0015, "front_white"),
                    0.0005, segments=3)
        round_edges(front_plate("button_cap", circle(b["cap"] / 2), b["x"], b["z"], py + 0.0015, py + 0.0045, "button_red"),
                    0.0008, segments=3)
    with parts.assembly("exposure_knob"):
        k = P["knob"]
        L, yw = k["length"], py + k["length"] * k["drum"]
        rd, rc = k["drum_d"] / 2, k["cap_d"] / 2
        # Behind: a white drum ruled by thin black lines (the lighten/darken scale) ...
        drum = ccyl("knob_drum", rd, yw - py, location=(k["x"], (py + yw) / 2, k["z"]), direction=(0, 1, 0),
                    material="front_white", segments=48)
        round_edges(drum, 0.0004, segments=2)
        for i in range(k["lines"]):
            a = 2 * math.pi * i / k["lines"]
            line = parts.box(f"knob_line_{i}", (0.0004, yw - py - 0.0012, 0.0003),
                             location=(k["x"] + rd * math.cos(a), (py + yw) / 2, k["z"] + rd * math.sin(a)),
                             material="body_black")
            line.rotation_euler = (0, math.pi / 2 - a, 0)
        # ... and in front the black cap: knurled round its back, smooth in front, its face dished.
        kn = yw + k["knurl"]
        ridges = [(rc * (1.0 if i % 2 else 0.95) * math.cos(math.pi * i / 36),
                   rc * (1.0 if i % 2 else 0.95) * math.sin(math.pi * i / 36)) for i in range(72)]
        round_edges(front_plate("knob_knurl", ridges, k["x"], k["z"], yw, kn, "body_black"), 0.0003, segments=2, angle=60)
        cap = front_ring("knob_cap", circle(rc * 0.97, 48), circle(rc * 0.78, 48), k["x"], k["z"], kn - 0.0002, py + L, "body_black",
                         inner_y0=py + L - 0.0015)
        round_edges(cap, 0.0006, segments=3)
        front_plate("knob_face", circle(rc * 0.8, 48), k["x"], k["z"], py + L - 0.0018, py + L - 0.0015, "body_black")
        # The pointer moulded into the plate between the viewfinder window and the knob.
        pt = k["pointer"]
        side_prism("knob_pointer", [(py, pt["z"] + pt["h"]), (py + 0.0006, pt["z"] + pt["h"]), (py, pt["z"])],
                   k["x"] - pt["w"] / 2, k["x"] + pt["w"] / 2, "front_white")
        # The knob turns on its axis (a click in the viewer turns it: the spec's joints.knob_turn).
        j = parts.joint("knob_turn", (k["x"], py, k["z"]), axis=(0, 1, 0))
        for o in [ob for ob in parts.collection().objects if ob.name.startswith(("knob_drum", "knob_line_", "knob_knurl", "knob_cap", "knob_face"))]:
            o.parent = j
            o.matrix_parent_inverse = j.matrix_world.inverted()
    with parts.assembly("badge"):
        bd = P["badge"]
        badge = parts.box("badge", (bd["width"], 0.0004, bd["height"]), location=(bd["x"], py + 0.0002, bd["z"]),
                          material=_image_material("badge", "badge.jpg", 0.5))
        _uv_plane(badge, 0, 2, bd["x"] + bd["width"] / 2, bd["x"] - bd["width"] / 2,
                  bd["z"] - bd["height"] / 2, bd["z"] + bd["height"] / 2)
    with parts.assembly("flash_socket"):
        # A flat grained pad with sloped edges and a long slot for the flash's plug (halicki_2023 (2)).
        fs = P["flash_socket"]
        top = P["front_section"]["top"]
        cy = P["white_cover_back"] - fs["depth"] / 2 + 0.004
        w, d, h, ch = fs["width"], fs["depth"], fs["height"], 0.0015
        verts = [(fs["x"] + sx * w / 2, cy + sy * d / 2, top - 0.0005) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))] + \
                [(fs["x"] + sx * (w / 2 - ch), cy + sy * (d / 2 - ch), top + h) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        pad = _solid("socket_pad", verts, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
                     "hood_matte")
        slot = parts.box("socket_slot_cut", (0.022, 0.0016, h * 2), location=(fs["x"], cy, top + h), material="hood_matte")
        m = pad.modifiers.new("slot", "BOOLEAN")
        m.operation, m.solver, m.object = "DIFFERENCE", "EXACT", slot
        _apply(pad)
        bpy.data.objects.remove(slot)
        round_edges(pad, 0.0004, segments=2, angle=20)
        # The plug's contacts at the bottom of the slot.
        parts.box("socket_contacts", (0.020, 0.0012, 0.0003), location=(fs["x"], cy, top + 0.0003), material="pick_brass")


def viewfinder_hood(P):
    """The hood over the viewfinder tube (returned, to be fused into the body): its top rises to
    the eyecup, its underside curves down into the sloped back (halicki_2023 (1), (2))."""
    e, fs, low = P["eyecup"], P["front_section"], P["lower_box"]
    slope = lambda y: low["height"] + (y - low["y0"]) * (fs["top"] - low["height"]) / (fs["y0"] - low["y0"])
    yr = e["y_rear"] + 0.008          # the hood's end, inside the eyecup
    yf = fs["y0"] + 0.006             # its front, inside the front frame
    zb = e["top"] - 0.026 + 0.002     # underside at the end, just above the eyecup's bottom
    ym = yr + 0.040                   # where the underside meets the sloped back
    poly = [(yf, fs["top"] - 0.001), (yr, e["top"] - 0.004), (yr, zb)]   # its front rises out of the frame's back
    for k in range(1, 7):             # quadratic curve from the end down to the slope
        s = k / 6
        a, b, c = Vector((yr, zb)), Vector((ym - 0.010, zb - 0.002)), Vector((ym, slope(ym)))
        q = a * (1 - s) ** 2 + b * 2 * s * (1 - s) + c * s * s
        poly.append((q.x, q.y))
    poly += [(ym + 0.004, slope(ym + 0.004) - 0.006), (yf, slope(yf) - 0.010)]
    with parts.assembly("body"):
        hood = side_prism("hood", poly, e["x"] - e["width"] / 2, e["x"] + e["width"] / 2, "hood_matte")
    with parts.assembly("eyecup"):
        # A rubber cap over the hood's end, a little larger all round, open for the eye.
        h, w = 0.026, e["width"] + 0.004
        cup = front_ring("eyecup", rrect(w, h, 0.006), rrect(e["width"] - 0.008, h - 0.010, 0.004),
                         e["x"], e["top"] - h / 2, e["y_rear"], e["y_rear"] + 0.016, "eyecup_rubber")
        round_edges(cup, 0.002, segments=3, angle=40)
        # Inside the rim: a flat face with a small square eyepiece hole, dark behind it.
        ep = P["eyepiece"]
        y = e["y_rear"] + ep["inset"]
        ep_ring = front_ring("eyepiece", rrect(e["width"] - 0.008, h - 0.010, 0.004), rrect(ep["hole"], ep["hole"], 0.0008),
                   e["x"], e["top"] - h / 2, y, y + 0.0015, "eyecup_rubber")
        round_edges(ep_ring, 0.0004, segments=2)
        # Behind the hole, the scene the camera is aimed at, as the eye sees it through the finder:
        # upright and the right way round (seen from behind, +x is on the right). Lit by itself a
        # little, as the finder brings in light from the front; the eyecup shades it otherwise.
        sw = ep["hole"] + 0.001
        scene = front_plate("eyepiece_scene", rrect(sw, sw, 0.0008), e["x"], e["top"] - h / 2,
                            y + 0.0015, y + 0.0025, _scene_material())
        _uv_plane(scene, 0, 2, e["x"] - sw / 2, e["x"] + sw / 2, e["top"] - h / 2 - sw / 2, e["top"] - h / 2 + sw / 2)
        # The viewer slides the picture with the viewing angle, as a distant scene would move
        # through the finder (estimates.viewfinder_parallax: the share shown and the slide).
        scene["parallax"] = [SPEC[0]["estimates"]["viewfinder_parallax"]["value"]["shown"],
                             SPEC[0]["estimates"]["viewfinder_parallax"]["value"]["slide"]]
    return hood


def grain_finishes(spec):
    """The moulded plastic's fine texture on every outside part: each plain finish named in the
    spec's surface_grain swapped for the same colour with a little mottle and a bump map of
    grain `cell` metres across and `depth` deep, on a `repeat`-metre tile (box-projected UVs)."""
    g = spec["estimates"]["surface_grain"]["value"]
    swap = {}
    for key, e in g["finishes"].items():
        m = spec["materials"][key]
        px, rep = 256, g["repeat"]
        mpp = rep / px
        h = tiling._noise(px, px, e["cell"] / mpp, e["cell"] / mpp, e["seed"])
        h += 0.5 * tiling._noise(px, px, e["cell"] / mpp / 2.5, e["cell"] / mpp / 2.5, e["seed"] + 7)
        h *= e["depth"]                                           # metres
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * mpp)
        dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * mpp)
        nrm = np.stack([-dx, -dy, np.ones_like(dx)], 2)
        nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
        mot = tiling._noise(px, px, 0.004 / mpp, 0.004 / mpp, e["seed"] + 3)
        col = tiling.srgb(m["hex"])[None, None] * (1 + e["mottle"] * mot)[..., None]
        base = tiling.image("polaroid1000", f"{key}_grain_base", np.clip(col, 0, 1).astype(np.float32), "sRGB")
        normal = tiling.image("polaroid1000", f"{key}_grain_normal", (nrm * 0.5 + 0.5).astype(np.float32), "Non-Color")
        swap[key] = materials.image(f"{key}_grain", base, normal, metallic=m.get("metallic", 0.0),
                                    roughness=m.get("roughness", 0.5))
    for obj in parts.collection().objects:
        if obj.type != "MESH" or obj.get("internal") or obj.get("inside"):
            continue
        slots = [sl for sl in obj.material_slots if sl.material and sl.material.name in swap]
        if not slots:
            continue
        if any(sl.material and sl.material.name not in swap and any(n.type == "TEX_IMAGE" for n in sl.material.node_tree.nodes)
               for sl in obj.material_slots):
            continue                                              # already UV-mapped for a picture
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])
        tiling.box_uv(obj, g["repeat"])
        for sl in slots:
            sl.material = swap[sl.material.name]


# --- inside -------------------------------------------------------------------------------

def optics(P, E):
    """Lens, shutter, the light box and its 45-degree mirror, laid out so the path from the lens
    to the film is the spec's light_path (estimates)."""
    zl, yl, zf, path = P["lens_centre_z"], E["lens_y"], E["film_plane_z"], E["light_path"]
    ym = yl + zl - zf - path            # where the lens axis meets the mirror
    c = zl - ym                         # mirror plane: z = y + c
    xl = P["lens_boss"]["x"]                # centred in the boss's window
    ya = P["front_plate"]["y"] - 0.002          # the shutter's opening, just behind the lens
    with parts.assembly("shutter_opening", inside=True):   # seen through the lens
        parts.lathe("shutter_disc", [(0, -0.0012), (0.0052, -0.0006), (0.0055, 0), (0.0052, 0.0006), (0, 0.0014)],
                    location=(xl, ya, zl), direction=(0, 1, 0), material="lens_glass", segments=32)
        ccyl("shutter_ring", 0.0068, 0.003, location=(xl, ya, zl), direction=(0, 1, 0),
                       material="body_black", segments=32, caps=False)
    shutter_block(P, E, xl, zl)
    # The mirror covers the cone from the lens to the 79 x 77 mm picture area. Unfolded about the
    # mirror, the film point (y, zf) sits at (zf - c, y + c).
    ix, iy = 0.079 / 2, 0.077 / 2
    L = Vector((0, yl, zl))
    ends = []
    for dy in (iy, -iy):
        d = Vector((0, zf - c, ym + dy + c)) - L
        t = (c - (L.z - L.y)) / (d.z - d.y)
        ends.append((L + d * t, t))
    (top, t_top), (bot, t_bot) = sorted(ends, key=lambda e: -e[0].z)
    top0, bot0 = top.copy(), bot.copy()
    up = (top - bot).normalized()
    top, bot = top + up * 0.002, bot - up * 0.002
    hx_top, hx_bot = ix * t_top + 0.002, ix * t_bot + 0.002
    with parts.assembly("mirror", internal=True):
        slab("mirror", [(hx_top, top.y, top.z), (-hx_top, top.y, top.z), (-hx_bot, bot.y, bot.z), (hx_bot, bot.y, bot.z)],
             Vector((0, -1, 1)), 0.0015, "mirror")
    with parts.assembly("light_box"):     # faded with the shell in Internal mode, so what it holds shows
        # One black moulding (retronautik_1000, the light box out of the camera): open over the
        # picture, its sides leaning in to a narrow top, the back wall carrying the mirror, a
        # window in the front wall for the light from the shutter; a steel frame round its foot.
        lbx = E["light_box"]
        t, mg = lbx["wall"], lbx["margin"]
        yf0, yf1 = ym - iy - mg, ym + iy + mg
        yfr = ya - 0.0075                     # the front wall, just behind the shutter
        zt = top.z + 0.003                    # the top, over the mirror's top edge
        bx, tx = ix + mg, hx_top + mg
        def pts(d, below=0.0):
            hx = lambda z: bx + (tx - bx) * (z - zf) / (zt - zf) - d
            k = 0.0035 - d * 1.414            # the sloped back wall: 3.5 mm behind the mirror's plane
            zk = yf0 + d + c + k              # where the upright back meets it
            zb = zf - below
            out = []
            for sx in (1, -1):
                out += [(sx * hx(zf), yf0 + d, zb), (sx * hx(zk), yf0 + d, zk),
                        (sx * hx(zt), zt - d - c - k, zt - d), (sx * hx(zt), yfr - d, zt - d),
                        (sx * hx(zf), yf1 - d, zb)]
            return out
        box = hull("light_box", pts(0.0), "lightbox_black")
        inner = hull("light_box_inner", pts(t, 0.01), "lightbox_black")
        m = box.modifiers.new("hollow", "BOOLEAN")
        m.operation, m.solver, m.object = "DIFFERENCE", "EXACT", inner
        _apply(box)
        bpy.data.objects.remove(inner)
        cut(box, (lbx["window"][0], 0.01, lbx["window"][1]), (xl, yfr, zl))
        # The fine upright ribs on the inside of the far wall.
        hxz = lambda z: bx + (tx - bx) * (z - zf) / (zt - zf)
        k = 0.0035
        y_front = lambda z: yf1 + (yfr - yf1) * (z - zf) / (zt - zf) - t
        rb = lbx["ribs"]
        verts, faces = [], []
        y = yf0 + t + 0.002
        while y + rb["width"] < y_front(zt) - 0.002:
            za, zb = zf + 0.002, min(zt - 0.002, y + c - 0.0025)      # stopping short of the mirror
            if zb - za > 0.004:
                i = len(verts)
                for z in (za, zb):
                    xs = hxz(z) - t
                    for yy in (y, y + rb["width"]):
                        verts += [(xs + 0.0001, yy, z), (xs - rb["depth"], yy, z)]
                faces += [(i, i + 2, i + 6, i + 4), (i + 1, i + 5, i + 7, i + 3), (i + 1, i + 3, i + 2, i),
                          (i + 4, i + 6, i + 7, i + 5), (i, i + 4, i + 5, i + 1), (i + 2, i + 3, i + 7, i + 6)]
            y += rb["pitch"]
        _solid("light_box_ribs", verts, faces, "lightbox_black")
        # The steel frame round the foot, with a tab turned up at each end.
        fw, fd, ft = lbx["frame"]["width"], lbx["frame"]["depth"], 0.0006
        frame = front_ring("light_box_frame", rrect(fw, fd, 0.001), rrect(2 * bx, yf1 - yf0, 0.0005), 0, 0, 0, ft, "frame_steel")
        frame.rotation_euler = (math.pi / 2, 0, 0)
        frame.location = (0, (yf0 + yf1) / 2, zf + ft)
        _apply_transform(frame)
        for sx in (1, -1):
            parts.box(f"frame_tab_{'p' if sx > 0 else 'm'}", (ft, 0.012, 0.010),
                      location=(sx * (fw / 2 - ft / 2), (yf0 + yf1) / 2, zf + 0.005), material="frame_steel")
    with parts.assembly("light_path", internal=True):
        # The light from the lens to the mirror and from the mirror down onto the picture area,
        # as a faint envelope ...
        mat = glow("light_bundle", SPEC[0], 0.08, 0.3)
        m = [Vector((ix * t_top, top0.y, top0.z)), Vector((-ix * t_top, top0.y, top0.z)),
             Vector((-ix * t_bot, bot0.y, bot0.z)), Vector((ix * t_bot, bot0.y, bot0.z))]
        film = [Vector((ix, ym + iy, zf + 0.0003)), Vector((-ix, ym + iy, zf + 0.0003)),
                Vector((-ix, ym - iy, zf + 0.0003)), Vector((ix, ym - iy, zf + 0.0003))]
        verts = [tuple(L)] + [tuple(v) for v in m]
        _solid("light_to_mirror", verts, [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (1, 4, 3, 2)], mat)
        # Mirror corners pair with film corners: the top of the mirror lights the film's front edge.
        verts = [tuple(v) for v in m] + [tuple(v) for v in film]
        _solid("light_to_film", verts, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1), (4, 5, 6, 7)], mat)
        # ... and nine rays, coloured by where in the scene they come from: each starts in front
        # of the camera, crosses at the lens, folds at the mirror and lands on the film, so the
        # top of the scene lands at one edge of the print and the bottom at the other.
        cols = {}
        for key in ("ray_top", "ray_centre", "ray_bottom"):
            cols[key] = glow(key, SPEC[0], 0.95, 0.7)
        for i, fy in enumerate((iy * 0.85, 0.0, -iy * 0.85)):
            for j, fx in enumerate((ix * 0.85, 0.0, -ix * 0.85)):
                P = Vector((fx, ym + fy, zf + 0.0003))            # on the film
                V = Vector((fx, zf - c, ym + fy + c))             # the same point unfolded about the mirror
                d = V - L
                t = (c - (L.z - L.y)) / (d.z - d.y)
                M = L + d * t                                      # where it meets the mirror
                S = L - d.normalized() * 0.07                      # 70 mm in front of the lens
                key = "ray_centre" if fy == 0 else ("ray_top" if S.z > L.z else "ray_bottom")
                parts.tube(f"ray_{i}{j}", [tuple(S), tuple(L), tuple(M), tuple(P)], 0.00035, segments=6,
                           material=cols[key])
                parts.disc(f"ray_spot_{i}{j}", 0.0012, 0.0002, location=(fx, ym + fy, zf + 0.0004), material=cols[key])
    return ym


def shutter_block(P, E, xl, zl):
    """The shutter and electronics block behind the front plate (retronautik_1000, 'Verschluss,
    Mechanik und Elektrik'): a black frame carrying the lens cup with the shutter's opening, the
    silver shutter blade, the gear and its red winding, the exposure knob's barrel; the flex foil
    down to the switch contacts, and the arm with the frame counter. Sizes in estimates."""
    sb = E["shutter_block"]
    pl, cp = sb["plate"], sb["cup"]
    y0, y1 = pl["y0"], pl["y0"] + pl["t"]
    k = P["knob"]
    with parts.assembly("shutter_block", internal=True):
        # The frame: round the cup, out to the knob's barrel on one side and the gear on the other,
        # clear of the viewfinder tube above the knob.
        outline = [(0.045, 0.016), (0.012, 0.0175), (-0.012, 0.0175), (-0.020, 0.008), (-0.024, -0.003),
                   (-0.040, -0.008), (-0.042, -0.020), (-0.040, -0.026), (-0.020, -0.026), (0.045, -0.026)]
        frame = front_ring("shutter_frame", outline, circle(pl["hole_d"] / 2), xl, zl, y0, y1, "body_black")
        round_edges(frame, 0.0004, segments=2)
        # The lens cup: a thick rim, a step, then a cone in to the opening in the frame.
        ro, ri, rs, d, st = cp["d"] / 2, cp["rim_d"] / 2, cp["step_d"] / 2, cp["depth"], cp["step_at"]
        parts.lathe("lens_cup", [(pl["hole_d"] / 2 + 0.0003, 0), (ro, 0), (ro, d), (ri, d), (ri, st), (rs, st),
                                 (rs, 0.0012), (pl["hole_d"] / 2 + 0.0003, 0.0003)],
                    location=(xl, y1, zl), direction=(0, 1, 0), closed=True, segments=48, material="body_black")
        # The exposure knob's barrel: a black tube on the frame, behind the knob.
        br = sb["barrel"]
        parts.lathe("knob_barrel", [(br["d"] / 2 - br["wall"], 0), (br["d"] / 2, 0), (br["d"] / 2, d), (br["d"] / 2 - br["wall"], d)],
                    location=(k["x"], y1, k["z"]), direction=(0, 1, 0), closed=True, segments=32, material="body_black")
        # The shutter blade: a dimpled steel crescent on the frame, below the cup on the gear side.
        bl = sb["blade"]
        n = 12
        arc = lambda r, rev: [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
                              for a in (bl["a0"] + (bl["a1"] - bl["a0"]) * i / n for i in (range(n, -1, -1) if rev else range(n + 1)))]
        front_plate("shutter_blade", arc(bl["r1"], False) + arc(bl["r0"], True), xl, zl, y1, y1 + 0.0003, "frame_steel")
        # The gear (axis forward) and, below it, the red winding.
        g = sb["gear"]
        gr = gear("shutter_gear", g["d"] / 2, 0.0012, (0, 0, 0), "body_black")
        gr.rotation_euler = (0, 0, math.pi / 2)
        gr.location = (xl + g["u"], y1 + 0.0009, zl + g["v"])
        _apply_transform(gr)
        c = sb["coil"]
        cx, cz, cy = xl + c["u"], zl + c["v"], y1 + c["d"] / 2 + 0.001
        ccyl("coil", c["d"] / 2, c["length"], location=(cx, cy, cz), direction=(1, 0, 0), material="coil_red", segments=24)
        for sx in (1, -1):
            ccyl(f"coil_end_{'p' if sx > 0 else 'm'}", c["d"] / 2 + 0.0008, 0.0008, location=(cx + sx * (c["length"] / 2 + 0.0004), cy, cz),
                 direction=(1, 0, 0), material="body_black", segments=24)
        # The switch contacts: brass fingers on a black block low on the gear side.
        ct = sb["contacts"]
        cb = parts.box("contact_block", (0.008, ct["y1"] - ct["y0"], 0.006), location=(ct["x"], (ct["y0"] + ct["y1"]) / 2, ct["z"]),
                       material="body_black")
        round_edges(cb, 0.0004, segments=2)
        for i in range(ct["fingers"]):
            parts.box(f"contact_finger_{i}", (0.0011, ct["y1"] - ct["y0"] - 0.002, 0.0004),
                      location=(ct["x"] - 0.0027 + i * 0.0018, (ct["y0"] + ct["y1"]) / 2, ct["z"] + 0.0032), material="pick_brass")
        # The flex foil from under the frame down to the contacts.
        zt, zb = zl - 0.024, ct["z"] + 0.003
        parts.box("flex_foil", (0.010, 0.0003, zt - zb), location=(ct["x"] - 0.005, ct["y0"] - 0.00015, (zt + zb) / 2),
                  material="flex_foil")
        # The arm: a black channel back along the wall, toothed underneath, a steel rod and a hook on
        # top; the frame counter's white wheel at its front, in a cheek.
        a = sb["arm"]
        teeth = []
        yt0, yt1, pitch = a["y0"] + 0.012, a["y1"] - 0.006, 0.0012
        nt = int((yt1 - yt0) / pitch)
        for i in range(nt):
            yy = yt1 - i * pitch
            teeth += [(yy, a["z0"]), (yy - pitch * 0.3, a["z0"] - 0.0006), (yy - pitch * 0.7, a["z0"] - 0.0006)]
        arm = side_prism("counter_arm", [(a["y1"], a["z0"])] + teeth + [(a["y0"], a["z0"]), (a["y0"], a["z1"] + 0.004),
                                                                         (a["y0"] + 0.003, a["z1"] + 0.004), (a["y0"] + 0.003, a["z1"]),
                                                                         (a["y1"], a["z1"])], a["x0"], a["x1"], "body_black")
        ccyl("arm_rod", 0.0014, 0.030, location=((a["x0"] + a["x1"]) / 2, a["y0"] + 0.028, a["z1"] + 0.0014), direction=(0, 1, 0),
             material="frame_steel", segments=16)
        cn = sb["counter"]
        drum = ccyl("counter_wheel", cn["d"] / 2, cn["width"], location=(cn["x"], cn["y"], cn["z"]), direction=(1, 0, 0),
                    material="front_white", segments=32)
        parts.box("counter_cheek", (0.001, cn["d"] + 0.002, cn["d"] + 0.003), location=(cn["x"] - cn["width"] / 2 - 0.0012, cn["y"], cn["z"]),
                  material="body_black")

def film(E, ym):
    pk, zf = E["pack"], E["film_plane_z"]
    y0, z0 = pk["front_y"] - pk["y"], zf - pk["z"]
    yc = (y0 + pk["front_y"]) / 2
    with parts.assembly("film_pack", internal=True):
        parts.box("pack_case", (pk["x"], pk["y"], pk["z"] - 0.0006), location=(0, yc, z0 + (pk["z"] - 0.0006) / 2),
                  material="body_black")
    print_sheet(E, ym)
    with parts.assembly("battery", internal=True):
        b = E["battery"]
        parts.box("battery", (b["x"], b["y"], b["z"]), location=(0, yc, z0 + 0.0006 + b["z"] / 2), material="dark_metal")
        for sgn in (1, -1):
            parts.box(f"contact_{'p' if sgn > 0 else 'm'}", (0.006, 0.008, 0.0004),
                      location=(sgn * 0.012, pk["front_y"] - 0.004, z0 - 0.0002), material="pick_brass")
    with parts.assembly("pack_springs", internal=True):
        for sgn in (1, -1):
            parts.box(f"spring_{'p' if sgn > 0 else 'm'}", (0.006, 0.07, 0.0004),
                      location=(sgn * 0.03, yc, z0 - 0.0008), material="frame_steel")


def print_sheet(E, ym):
    """The top print in the pack, its picture centred under the mirror, its wide (pod) border
    toward the rollers, so it leaves the camera pod first. Its face shows the picture (refs
    print.jpg); over it the blue-green layer that clears as it develops (the viewer fades it out
    over the time in its "fade_out")."""
    pr, zf = E["print"], E["film_plane_z"]
    hx = pr["x"] / 2
    yr = ym - pr["picture"][1] / 2 - pr["narrow_border"]       # its trailing (rear) edge
    yf = yr + pr["y"]
    with parts.assembly("print", inside=True):   # solid in Internal mode; out of the slot it shows outside too
        card = parts.box("print_card", (pr["x"], pr["y"], pr["t"] - 0.00004), location=(0, (yr + yf) / 2, zf - pr["t"] / 2 - 0.00002),
                         material="print_back")
        face = slab("print_face", [(hx, yr, zf), (-hx, yr, zf), (-hx, yf, zf), (hx, yf, zf)], Vector((0, 0, 1)), 0.00002,
                    _image_material("print", "print.jpg", 0.3))
        # Seen from above with its narrow border at the rear, the picture's top is at the rear and its
        # right on -x (the lens turns the scene over; the mirror turns it back the right way round).
        _uv_plane(face, 0, 1, hx, -hx, yf, yr)
        pw, ph = pr["picture"]
        y0 = yr + pr["narrow_border"]
        dev = slab("print_developer", [(pw / 2, y0, zf + 0.00004), (-pw / 2, y0, zf + 0.00004), (-pw / 2, y0 + ph, zf + 0.00004),
                                       (pw / 2, y0 + ph, zf + 0.00004)], Vector((0, 0, 1)), 0.00002, "print_developing")
        dev["fade_out"] = list(E["capture"]["develop"])
    ANIM["print"] = [card, face, dev]


def drive(E):
    r, zf, pk, m = E["rollers"], E["film_plane_z"], E["pack"], E["motor"]
    ru, rl = r["upper_d"] / 2, r["lower_d"] / 2
    rf = E["roller_frame"]
    L, ry = r["length"], r["y"]
    za = zf + ru                                  # the gold roller's axle
    with parts.assembly("rollers", internal=True):
        # The gold roller, its ends turned down to the axle; the steel roller with thin journals.
        parts.lathe("upper_roller", [(0, -L / 2 - 0.002), (0.0012, -L / 2 - 0.002), (0.0012, -L / 2), (ru * 0.85, -L / 2),
                                     (ru, -L / 2 + 0.003), (ru, L / 2 - 0.003), (ru * 0.85, L / 2), (0.0012, L / 2),
                                     (0.0012, L / 2 + 0.006), (0, L / 2 + 0.006)],
                    location=(0, ry, za), direction=(1, 0, 0), segments=24, material="roller_gold")
        jr, jl = rf["journal"]["d"] / 2, rf["journal"]["length"]
        parts.lathe("lower_roller", [(0, -L / 2 - jl), (jr, -L / 2 - jl), (jr, -L / 2), (rl, -L / 2 + 0.0004), (rl, L / 2 - 0.0004),
                                     (jr, L / 2), (jr, L / 2 + jl), (0, L / 2 + jl)],
                    location=(0, ry, zf - rl), direction=(1, 0, 0), segments=24, material="roller_steel")
        # The steel roller's ends sit in the body's two bearing blocks.
        for sgn in (1, -1):
            parts.box(f"roller_bearing_{'p' if sgn > 0 else 'm'}", (0.0025, 0.006, 0.004),
                      location=(sgn * (L / 2 + jl - 0.00125), ry, zf - rl), material="body_black")
        # The strip over the gold roller, its ends bent down to the axle; two long slots in it.
        st = rf["strip"]
        zs = za + st["above_axle"]
        strip = parts.box("roller_strip", (L + 0.002, st["width"], st["t"]), location=(0, ry, zs + st["t"] / 2),
                          material="frame_steel")
        for x, ln in st["slots"]:
            cut(strip, (ln, st["slot_w"], 0.01), (x, ry, zs))
        x_end = L / 2 + 0.0023
        # The far end: a plain tab down to the axle.
        side_prism("strip_end_m", [(ry - 0.003, za - 0.0025), (ry + 0.003, za - 0.0025), (ry + 0.003, zs + st["t"]),
                                   (ry - 0.003, zs + st["t"])], -x_end - 0.0006, -x_end, "frame_steel")
        # The gear end: a plate reaching back past the axle to a hook (the door's catch).
        la = rf["latch"]
        yb = ry - la["back"]
        side_prism("strip_end_p", [(ry + 0.0036, zs + st["t"]), (ry + 0.0036, za - 0.0025), (ry - 0.004, za - 0.0025),
                                   (yb + 0.003, za - 0.002), (yb + 0.003, za - la["hook_drop"]), (yb, za - la["hook_drop"]),
                                   (yb, za + 0.004), (ry - 0.004, zs - 0.002), (ry - 0.0036, zs + st["t"])],
                   x_end, x_end + 0.0006, "frame_steel")
        # The brass spring under the steel roller: a plate with three tines along it.
        fk = rf["fork"]
        zk = zf - 2 * rl - fk["t"] - 0.0001
        x0 = -fk["length"] / 2
        tw = fk["width"] / (2 * fk["tines"] - 1)
        poly = [(x0, ry - fk["width"] / 2), (x0 + fk["length"] - fk["tine_length"], ry - fk["width"] / 2)]
        for i in range(fk["tines"]):
            yy = ry - fk["width"] / 2 + 2 * i * tw
            poly += [(x0 + fk["length"], yy), (x0 + fk["length"], yy + tw)]
            if i < fk["tines"] - 1:
                poly += [(x0 + fk["length"] - fk["tine_length"], yy + tw), (x0 + fk["length"] - fk["tine_length"], yy + 2 * tw)]
        poly += [(x0, ry + fk["width"] / 2)]
        verts = [(u, v, zk) for u, v in poly] + [(u, v, zk + fk["t"]) for u, v in poly]
        n = len(poly)
        bm_faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        fork = _solid("roller_spring", verts, bm_faces, "pick_brass")
        cut(fork, (0.003, 0.0025, 0.01), (x0 + 0.010, ry, zk))
    with parts.assembly("pick", internal=True):
        # Beside the print on the pack, a tab turned in behind the print's trailing edge.
        pr = E["print"]
        yr = E["_ym"] - pr["picture"][1] / 2 - pr["narrow_border"]
        ANIM["pick"] = [parts.box("pick_tab", (0.0035, 0.0006, 0.0006), location=(0.04225, yr - 0.0003, zf - 0.0003), material="pick_brass")]
        ANIM["pick"].append(parts.box("pick_plate", (0.005, 0.07, 0.0004), location=(0.0465, yr + 0.035 - 0.0006, zf - 0.0004),
                                      material="pick_brass"))
    gt = E["gear_train"]
    p1, p2, p3 = gt["planes"]
    mx, my, mz = m["x"], m["y"], m["z"]
    with parts.assembly("motor", internal=True):
        # A flat-sided can across the front, its black end bell away from the rail, the shaft
        # running out to the gear train (ifixit_onestep600 step 18).
        can = ccyl("motor_can", m["width"] / 2, m["length"], location=(mx, my, mz), direction=(1, 0, 0),
                   material="foil_silver", segments=32)
        for sz in (1, -1):
            cut(can, (0.03, 0.03, 0.01), (mx, my, mz + sz * (m["flat"] / 2 + 0.005)))
        ccyl("motor_bell", m["bell_d"] / 2, m["bell"], location=(mx - m["length"] / 2 - m["bell"] / 2, my, mz), direction=(1, 0, 0),
             material="body_black", segments=24)
        x0 = mx + m["length"] / 2
        ccyl("motor_shaft", m["shaft_d"] / 2, p1 + gt["width"] / 2 - x0, location=((x0 + p1 + gt["width"] / 2) / 2, my, mz),
             direction=(1, 0, 0), material="frame_steel", segments=12)
    with parts.assembly("gear_train", internal=True):
        # Motor pinion -> two white compound gears -> the gold roller's black gear, in three planes
        # beside the roller frame. The chain bends upward between its ends.
        P0, P3 = Vector((my, mz)), Vector((r["y"], zf + ru))
        d1, d2, d3 = gt["motor_pinion"] + gt["a"]["r"], gt["a"]["pinion"] + gt["b"]["r"], gt["b"]["pinion"] + gt["roller_gear_d"] / 2
        u = (P3 - P0).normalized()
        n = Vector((-u.y, u.x))
        if n.y < 0:
            n = -n
        P1 = P0 + (u * math.cos(0.25) + n * math.sin(0.25)) * d1
        D = (P3 - P1).length
        assert abs(d2 - d3) < D < d2 + d3, "gear chain can't span the motor to the roller"
        aa = (d2 ** 2 - d3 ** 2 + D ** 2) / (2 * D)
        h = math.sqrt(max(d2 ** 2 - aa ** 2, 0.0))
        w = (P3 - P1).normalized()
        nw = Vector((-w.y, w.x))
        P2 = P1 + w * aa + (nw if nw.y > 0 else -nw) * h
        wd = gt["width"]
        def g(name, rad, plane, c, mat):
            gear(name, rad, wd, (plane, c.x, c.y), mat, module=0.0004)
        g("motor_pinion", gt["motor_pinion"], p1, P0, "frame_steel")
        g("gear_a", gt["a"]["r"], p1, P1, "front_white")
        g("gear_a_pinion", gt["a"]["pinion"], p2, P1, "front_white")
        g("gear_b", gt["b"]["r"], p2, P2, "front_white")
        g("gear_b_pinion", gt["b"]["pinion"], p3, P2, "front_white")
        g("roller_gear", gt["roller_gear_d"] / 2, p3, P3, "body_black")
        ANIM["gears"] = {"motor": (p1, P0), "a": (p1, P1), "b": (p2, P2), "roller": (p3, P3)}
    with parts.assembly("wiring", internal=True):
        # From the battery's contacts up to the switch contacts under the shutter block.
        z0, ct = zf - pk["z"], E["shutter_block"]["contacts"]
        for k, (sgn, mat) in enumerate(((1, "button_red"), (-1, "body_black"))):
            x = sgn * 0.012
            yw = pk["front_y"] - 0.004 - 0.006 * k          # the second wire runs clear of the first contact
            pts = [(x, pk["front_y"] - 0.004, z0 - 0.0006)] + ([(x, yw, z0 - 0.0011)] if k else []) + \
                  [(0.048, yw, z0 - 0.0011), (0.048, yw - 0.002, zf + 0.004),
                   (ct["x"] - 0.002 * sgn, ct["y1"] - 0.003, ct["z"] - 0.0032)]
            parts.tube(f"wire_{k}", pts, 0.0005, segments=8, bend_radius=0.002, material=mat)


def viewfinder_optics(P, E):
    """The viewfinder: a separate black channel from the front window to the eyepiece, open on top
    between its end blocks, a glass block in the front and a square element a third of the way
    from the rear (retronautik_1000, 'Sucher')."""
    vw, e, t = P["viewfinder_window"], P["eyecup"], E["viewfinder_tube"]
    F = Vector((vw["x"], t["y_front"], vw["z"]))
    R = Vector((vw["x"], t["y_rear"], e["top"] - 0.013))    # level with the eyepiece's centre (the tube still covers its hole)
    L = (R - F).length
    M = Matrix.Translation(F) @ (R - F).normalized().to_track_quat("-Y", "Z").to_matrix().to_4x4()
    w, h, wl = t["width"], t["height"], t["wall"]
    pieces = []    # each built at the origin, its mesh moved along the axis
    with parts.assembly("viewfinder_optics", internal=True):
        def box(name, size, at, mat="lightbox_black"):
            o = parts.box(name, size, material=mat)
            o.data.transform(M @ Matrix.Translation(at))
            pieces.append(o)
        for sx in (1, -1):
            box(f"finder_side_{'p' if sx > 0 else 'm'}", (wl, L, h), (sx * (w - wl) / 2, -L / 2, 0))
        box("finder_floor", (w - 2 * wl, L, wl), (0, -L / 2, -(h - wl) / 2))
        c, rb = t["collar"], t["rear_block"]
        box("finder_collar", (w + 0.002, c, h + 0.002), (0, -c / 2, 0))
        box("finder_rear", (w + 0.002, rb, h + 0.002), (0, -L + rb / 2, 0))
        # The glass: a block in the collar, the square element in its slots, the eyepiece lens.
        box("finder_front_lens", (w - 0.002, 0.003, h - 0.002), (0, 0.0002, 0), "lens_glass")
        ym = -L + (L - c - rb) * t["mid_lens_at"] + rb
        box("finder_mid_lens", (w - 2 * wl, t["lens_t"], h - 2 * wl), (0, ym, 0.0005), "lens_glass")
        for sx in (1, -1):
            box(f"finder_slot_{'p' if sx > 0 else 'm'}", (0.0012, t["lens_t"] + 0.002, h), (sx * (w / 2 - wl - 0.0006), ym, 0))
        box("eyepiece_lens", (w - 0.006, 0.002, h - 0.005), (0, -L - 0.001, 0), "lens_glass")
    with parts.assembly("finder_light", internal=True):
        # Its own light: rays from the scene through the front window, past the square element,
        # gathering at the eyepiece and on to the eye behind the eyecup.
        mat = glow("ray_finder", SPEC[0], 0.95, 0.7)
        u = (R - F).normalized()
        R3 = M.to_3x3()
        py = P["front_plate"]["y"]
        mid = F + u * (L - (L - c - rb) * t["mid_lens_at"] - rb)
        eye = R + u * 0.02
        for k, (a, b) in enumerate(((0, 0), (0.007, 0.005), (-0.007, 0.005), (0.007, -0.005), (-0.007, -0.005))):
            o = R3 @ Vector((a, 0, b))
            W = F + u * ((py - F.y) / u.y) + o
            Mi = mid + o * 0.5
            S = W + (W - Mi).normalized() * 0.06
            parts.tube(f"finder_ray_{k}", [tuple(S), tuple(W), tuple(Mi), tuple(R), tuple(eye)], 0.00035, segments=6,
                       material=mat)


SPEC = [None]
ANIM = {}          # parts the capture moves, and their pivots, gathered while building


# --- the capture ----------------------------------------------------------------------------

def capture(P, E, turn):
    """One picture, keyframed (sx70_service: the button starts the cycle, the shutter opens and
    closes, the motor drives the pick and the rolls, which break the pod, spread the developer and
    eject the print; the counter turns). Times in estimates.capture. Called after the model is
    turned, so pivots and moves go through `turn`; a turn of 180 degrees about z reverses x and y,
    so a turn about x or y runs the other way."""
    cp, r, gt, zf = E["capture"], E["rollers"], E["gear_train"], E["film_plane_z"]
    sc = bpy.context.scene
    fps = cp["fps"]
    sc.render.fps = fps
    n = int(round(cp["end"] * fps))
    sc.frame_start, sc.frame_end = 0, n
    ob = bpy.data.objects

    def pivot(o, p_cam):
        p = turn @ Vector(p_cam)
        W = o.matrix_basis.copy()                  # unparented: its own transform is its world one
        o.data.transform(Matrix.Translation(-p) @ W)
        o.matrix_basis = Matrix.Translation(p)
        o.rotation_mode = "XYZ"

    def ramp(t, t0, t1):
        return 0.0 if t <= t0 else 1.0 if t >= t1 else (t - t0) / (t1 - t0)

    def smooth(t, t0, t1):
        u = ramp(t, t0, t1)
        return u * u * (3 - 2 * u)

    # The print's travel: still until the motor starts, then steady to the end of the eject.
    t_m0, t_m1, travel = cp["motor"][0], cp["motor"][1], cp["travel"]
    s_at = lambda t: travel * ramp(t, t_m0, t_m1)
    ru, rl = r["upper_d"] / 2, r["lower_d"] / 2
    rg, bp, br, ap, ar, mp = gt["roller_gear_d"] / 2, gt["b"]["pinion"], gt["b"]["r"], gt["a"]["pinion"], gt["a"]["r"], gt["motor_pinion"]
    lb = P["lens_boss"]
    sb = E["shutter_block"]
    xl, zl = lb["x"], P["lens_centre_z"]
    y1 = sb["plate"]["y0"] + sb["plate"]["t"]
    G = ANIM["gears"]
    cn = sb["counter"]
    # (object names, pivot in the camera's frame, axis 0 = x / 1 = y, angle in the camera's frame at time t)
    turners = [
        (["upper_roller", "roller_gear"], (0, r["y"], zf + ru), 0, lambda t: s_at(t) / ru),
        (["lower_roller"], (0, r["y"], zf - rl), 0, lambda t: -s_at(t) / rl),
        (["gear_b", "gear_b_pinion"], (0, G["b"][1].x, G["b"][1].y), 0, lambda t: -s_at(t) / ru * rg / bp),
        (["gear_a", "gear_a_pinion"], (0, G["a"][1].x, G["a"][1].y), 0, lambda t: s_at(t) / ru * rg / bp * br / ap),
        # The motor would turn ar/mp times faster again (about 9000 rpm), more than the frames can
        # show: drawn at most cp["motor_cap"] radians a frame.
        (["motor_shaft", "motor_pinion"], (0, G["motor"][1].x, G["motor"][1].y), 0,
         lambda t: -min(s_at(t) / ru * rg / bp * br / ap * ar / mp, cp["motor_cap"] * fps * max(0.0, t - t_m0))),
        (["shutter_gear"], (xl + sb["gear"]["u"], 0, zl + sb["gear"]["v"]), 1,
         lambda t: math.radians(cp["shutter_turn"]) * (smooth(t, *cp["shutter_open"]) - smooth(t, *cp["shutter_close"]))),
        (["shutter_blade"], (xl, 0, zl), 1,
         lambda t: math.radians(cp["blade_turn"]) * (smooth(t, *cp["shutter_open"]) - smooth(t, *cp["shutter_close"]))),
        (["counter_wheel"], (cn["x"], cn["y"], cn["z"]), 0, lambda t: math.radians(36) * smooth(t, *cp["counter"])),
    ]
    for names, pc, axis, ang in turners:
        for nm in names:
            pivot(ob[nm], pc)
    # Things that slide: (objects, direction in the camera's frame, distance at time t)
    feed = cp["pick_feed"]
    t_feed = t_m0 + feed / (travel / (t_m1 - t_m0))
    sliders = [
        (["button_cap"], (0, -1, 0), lambda t: cp["button_travel"] * (smooth(t, *cp["press"]) - smooth(t, *cp["release"]))),
        ([o.name for o in ANIM["print"]], (0, 1, 0), s_at),
        ([o.name for o in ANIM["pick"]], (0, 1, 0), lambda t: min(s_at(t), feed) - feed * smooth(t, t_feed, t_feed + 0.3)),
    ]
    rest = {nm: ob[nm].location.copy() for names, _, _ in sliders for nm in names}
    for f in range(n + 1):
        t = f / fps
        for names, pc, axis, ang in turners:
            a = -ang(t)                                # the turn reverses x and y
            for nm in names:
                o = ob[nm]
                o.rotation_euler = (a, 0, 0) if axis == 0 else (0, a, 0)
                o.keyframe_insert("rotation_euler", frame=f)
        for names, d, dist in sliders:
            dv = turn.to_3x3() @ Vector(d) * dist(t)
            for nm in names:
                o = ob[nm]
                o.location = rest[nm] + dv
                o.keyframe_insert("location", frame=f)
    for o in ob:
        if o.animation_data and o.animation_data.action:
            for fc in o.animation_data.action.fcurves if hasattr(o.animation_data.action, "fcurves") else []:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    sc.frame_set(0)


def build(spec):
    SPEC[0] = spec
    P = {k: v["value"] for k, v in spec["from_photos"].items()}
    E = {k: v["value"] for k, v in spec["estimates"].items() if isinstance(v, dict)}
    shell(P)
    front_parts(P)
    ym = optics(P, E)
    E["_ym"] = ym
    film(E, ym)
    drive(E)
    viewfinder_optics(P, E)
    grain_finishes(spec)
    # The spec's positions are in the camera's own frame (lens along +y, button on +x). Turn the
    # whole model 180 degrees about z so it faces the viewer's front (-y, as Perseverance's).
    turn = Matrix.Rotation(math.pi, 4, "Z")
    for obj in parts.collection().objects:
        if obj.parent is None:
            obj.matrix_world = turn @ obj.matrix_world
    capture(P, E, turn)
