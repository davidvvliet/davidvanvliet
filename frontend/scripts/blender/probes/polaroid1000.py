# Polaroid Land Camera 1000 (Supercolor 1000). Built from lib/parts in metres; every number comes
# from specs/polaroid1000.json (with its source) or is marked here as estimated.
# Frame while building: z up, bottom at z = 0, centred; the lens along +y, +x the button side (the
# spec's frame). build() turns the result 180 degrees about z: the model faces -y.
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

from lib import materials, parts

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "refs", "polaroid1000")
HALF_W = 0.0535  # half the 107 mm width


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


def slab(name, corners, normal, t, material):
    """A thin plate on four world corners, thickness t along `normal`."""
    nv = Vector(normal).normalized() * t
    a = [Vector(c) for c in corners]
    verts = [tuple(v) for v in a] + [tuple(v + nv) for v in a]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return _solid(name, verts, faces, material)


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
        side_prism("lower_box", [(low["y0"], 0.0), (door["y0"], 0.0), (door["y0"], low["height"]),
                                 (low["y0"], low["height"])], -HALF_W, HALF_W, "body_black")
        side_prism("front_frame", [(fs["y0"], low["height"]), (wb, low["height"]), (wb, fs["top"]),
                                   (fs["y0"], fs["top"])], -HALF_W, HALF_W, "body_black")
        # The pyramid over the mirror: its back slopes down to the rear wall and its sides lean
        # in (7 mm inset at the top, estimated from halicki_2023 (1) and (2)).
        z0, z1, y0, y1, inset = low["height"], fs["top"], low["y0"], fs["y0"], 0.007
        verts = [(HALF_W, y0, z0), (-HALF_W, y0, z0), (-HALF_W, y1, z0), (HALF_W, y1, z0),
                 (HALF_W - inset, y1, z1), (-HALF_W + inset, y1, z1)]
        _solid("pyramid", verts, [(0, 1, 2, 3), (3, 2, 5, 4), (0, 4, 5, 1), (0, 3, 4), (1, 5, 2)], "body_black")
    with parts.assembly("film_door"):
        dz, dy0, dy1 = door["height"], door["y0"], door["y1"]
        slot = P["exit_slot"]
        hw = slot["half_width"]
        side_prism("door_body", [(dy0, 0.0), (dy1 - 0.006, 0.0), (dy1 - 0.006, dz), (dy0, dz)],
                   -HALF_W, HALF_W, "body_black")
        zs = (slot["z0"] + slot["z1"]) / 2
        parts.boxes("door_face", [
            ((2 * HALF_W, 0.006, slot["z0"]), (0, dy1 - 0.003, slot["z0"] / 2)),
            ((2 * HALF_W, 0.006, dz - slot["z1"]), (0, dy1 - 0.003, (dz + slot["z1"]) / 2)),
            ((HALF_W - hw, 0.006, slot["z1"] - slot["z0"]), ((HALF_W + hw) / 2, dy1 - 0.003, zs)),
            ((HALF_W - hw, 0.006, slot["z1"] - slot["z0"]), (-(HALF_W + hw) / 2, dy1 - 0.003, zs)),
        ], material="body_black")
        strip = parts.box("name_strip", (0.101, 0.0008, slot["label_z1"] - slot["label_z0"]),
                          location=(0, dy1 + 0.0004, (slot["label_z0"] + slot["label_z1"]) / 2),
                          material=_image_material("name_strip", "name-strip.jpg", 0.4))
        # The photo runs left to right as seen from the front, so +x is its left edge.
        _uv_plane(strip, 0, 2, 0.0505, -0.0505, slot["label_z0"], slot["label_z1"])
    with parts.assembly("door_latch"):
        la = P["door_latch"]
        parts.box("latch", (la["depth"], la["width"], la["height"]), location=(HALF_W + la["depth"] / 2, la["y"], la["z"]),
                  material="body_black")
    with parts.assembly("front_cover"):
        side_prism("white_cover", [(wb, door["height"]), (shelf["y"], door["height"]), (shelf["y"], shelf["z"]),
                                   (plate["y"], plate["bottom"]), (plate["y"], fs["top"]), (wb, fs["top"])],
                   -HALF_W, HALF_W, "front_white")
    stripe(P)


def stripe(P):
    """Five bands down the shelf, from the lens boss to the shelf's front edge, magenta on +x."""
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


def front_parts(P):
    py = P["front_plate"]["y"]
    lb = P["lens_boss"]
    with parts.assembly("lens_boss"):
        ow, oh, oz = lb["opening_w"], lb["opening_h"], lb["opening_z"]
        # The white frame (its hole off-centre: the top border is the widest) ...
        outer = [(u, v + lb["z"] - oz) for u, v in rrect(lb["width"], lb["height"], 0.007)]
        front_ring("boss", outer, rrect(ow, oh, 0.005), lb["x"], oz, py, py + lb["depth"], "front_white",
                   inner_y0=py + lb["depth"] - 0.0015)
        # ... and inside it the black stepped hood, narrowing back to the lens frame.
        steps = 6
        y = py + lb["depth"] - 0.0015
        dy = (y - py - 0.0005) / steps
        for k in range(steps):
            f0, f1 = k / steps, (k + 1) / steps
            w0, w1 = ow + (lb["lens_frame"] - ow) * f0, ow + (lb["lens_frame"] - ow) * f1
            h0, h1 = oh + (lb["lens_frame"] - oh) * f0, oh + (lb["lens_frame"] - oh) * f1
            zc = oz + (lb["lens_frame_z"] - oz) * f1
            front_ring(f"hood_step_{k}", [(u, v + (oz + (lb["lens_frame_z"] - oz) * f0) - zc) for u, v in rrect(w0, h0, 0.004)],
                       rrect(w1, h1, 0.0035), lb["x"], zc, y - dy, y, "body_black")
            y -= dy
        front_plate("hood_back", rrect(lb["lens_frame"], lb["lens_frame"], 0.0035), lb["x"], lb["lens_frame_z"],
                    py, py + 0.0005, "body_black")
    with parts.assembly("viewfinder_window"):
        vw = P["viewfinder_window"]
        front_ring("window_frame", rrect(vw["width"] + 0.003, vw["height"] + 0.003, 0.0015),
                   rrect(vw["width"], vw["height"], 0.001), vw["x"], vw["z"], py, py + 0.0015, "front_white")
        glass = front_plate("window_glass", rrect(vw["width"], vw["height"], 0.001), vw["x"], vw["z"],
                            py, py + 0.0005, _image_material("viewfinder_glass", "viewfinder.jpg", 0.05))
        _uv_plane(glass, 0, 2, vw["x"] + vw["width"] / 2, vw["x"] - vw["width"] / 2,
                  vw["z"] - vw["height"] / 2, vw["z"] + vw["height"] / 2)
    with parts.assembly("shutter_button"):
        b = P["button"]
        front_plate("button_bezel", circle(b["bezel"] / 2), b["x"], b["z"], py, py + 0.0015, "front_white")
        front_plate("button_cap", circle(b["cap"] / 2), b["x"], b["z"], py + 0.0015, py + 0.0045, "button_red")
    with parts.assembly("exposure_knob"):
        k = P["knob"]
        # Knurled: 24 ridges round the rim (halicki_2023 (3)).
        ridges = [((k["diameter"] / 2) * (1.0 if i % 2 else 0.93) * math.cos(math.pi * i / 24),
                   (k["diameter"] / 2) * (1.0 if i % 2 else 0.93) * math.sin(math.pi * i / 24)) for i in range(48)]
        front_plate("knob", ridges, k["x"], k["z"], py, py + k["length"], "body_black")
    with parts.assembly("badge"):
        bd = P["badge"]
        badge = parts.box("badge", (bd["width"], 0.0004, bd["height"]), location=(bd["x"], py + 0.0002, bd["z"]),
                          material=_image_material("badge", "badge.jpg", 0.5))
        _uv_plane(badge, 0, 2, bd["x"] + bd["width"] / 2, bd["x"] - bd["width"] / 2,
                  bd["z"] - bd["height"] / 2, bd["z"] + bd["height"] / 2)
    with parts.assembly("flash_socket"):
        fs = P["flash_socket"]
        top = P["front_section"]["top"]
        parts.box("socket_cover", (fs["width"], fs["depth"], fs["height"]),
                  location=(fs["x"], P["white_cover_back"] - fs["depth"] / 2 + 0.004, top + fs["height"] / 2),
                  material="eyecup_rubber")


def viewfinder_hood(P):
    e, fs, low = P["eyecup"], P["front_section"], P["lower_box"]
    top = fs["top"] + 0.001
    slope = lambda y: low["height"] + (y - low["y0"]) * (fs["top"] - low["height"]) / (fs["y0"] - low["y0"])
    with parts.assembly("viewfinder_hood"):
        # Its top rises from the front section to the eyecup (halicki_2023 (1), (2)).
        side_prism("hood", [(fs["y0"], top - 0.004), (fs["y0"], top), (e["y_rear"] + 0.008, e["top"] - 0.004),
                            (e["y_rear"] + 0.008, slope(e["y_rear"] + 0.008) + 0.002)],
                   e["x"] - e["width"] / 2, e["x"] + e["width"] / 2, "body_black")
    with parts.assembly("eyecup"):
        h = 0.026
        front_ring("eyecup", rrect(e["width"] + 0.002, h, 0.004), rrect(e["width"] - 0.006, h - 0.008, 0.003),
                   e["x"], e["top"] - h / 2, e["y_rear"], e["y_rear"] + 0.010, "eyecup_rubber")


# --- inside -------------------------------------------------------------------------------

def optics(P, E):
    """Lens, shutter, the light box and its 45-degree mirror, laid out so the path from the lens
    to the film is the spec's light_path (estimates)."""
    zl, yl, zf, path = P["lens_centre_z"], E["lens_y"], E["film_plane_z"], E["light_path"]
    ym = yl + zl - zf - path            # where the lens axis meets the mirror
    c = zl - ym                         # mirror plane: z = y + c
    with parts.assembly("lens", inside=True):   # seen through the boss
        parts.lathe("lens_element", [(0, -0.0012), (0.0052, -0.0006), (0.0055, 0), (0.0052, 0.0006), (0, 0.0014)],
                    location=(0, yl, zl), direction=(0, 1, 0), material="lens_glass", segments=32)
        ccyl("lens_cell", 0.0068, 0.003, location=(0, yl, zl), direction=(0, 1, 0),
                       material="body_black", segments=32, caps=False)
    with parts.assembly("shutter", internal=True):
        ccyl("shutter_plate", 0.013, 0.0015, location=(0, yl - 0.004, zl), direction=(0, 1, 0),
                       material="body_black", segments=40)
        for k, sgn in enumerate((1, -1)):
            parts.box(f"shutter_blade_{k}", (0.011, 0.0002, 0.007), location=(sgn * 0.003, yl - 0.003, zl + sgn * 0.001),
                      material="frame_steel")
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
    with parts.assembly("light_box", internal=True):
        yf0, yf1 = ym - iy - 0.002, ym + iy + 0.002
        yb = P["front_plate"]["y"] - 0.004   # behind the front plate
        poly = [(yf1, zf + 0.0015), (yb, zl - 0.012), (yb, zl + 0.012), (top.y, top.z + 0.002),
                (bot.y - 0.002, bot.z), (yf0, zf + 0.0015)]
        for sgn in (1, -1):
            side_prism(f"box_wall_{'p' if sgn > 0 else 'm'}", poly, sgn * 0.0435, sgn * 0.0445, "lightbox_black")
    with parts.assembly("light_path", internal=True):
        # The light from the lens to the mirror (a pyramid) and from the mirror down onto the
        # picture area (the folded image), drawn see-through.
        mat = glow("light_bundle", SPEC[0], 0.22, 0.6)
        m = [Vector((ix * t_top, top0.y, top0.z)), Vector((-ix * t_top, top0.y, top0.z)),
             Vector((-ix * t_bot, bot0.y, bot0.z)), Vector((ix * t_bot, bot0.y, bot0.z))]
        film = [Vector((ix, ym + iy, zf + 0.0003)), Vector((-ix, ym + iy, zf + 0.0003)),
                Vector((-ix, ym - iy, zf + 0.0003)), Vector((ix, ym - iy, zf + 0.0003))]
        verts = [tuple(L)] + [tuple(v) for v in m]
        _solid("light_to_mirror", verts, [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (1, 4, 3, 2)], mat)
        # Mirror corners pair with film corners: the top of the mirror lights the film's front edge.
        verts = [tuple(v) for v in m] + [tuple(v) for v in film]
        _solid("light_to_film", verts, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1), (4, 5, 6, 7)], mat)
    return ym


def film(E, ym):
    pk, zf = E["pack"], E["film_plane_z"]
    y0, z0 = pk["front_y"] - pk["y"], zf - pk["z"]
    yc = (y0 + pk["front_y"]) / 2
    with parts.assembly("film_pack", internal=True):
        parts.box("pack_case", (pk["x"], pk["y"], pk["z"] - 0.0006), location=(0, yc, z0 + (pk["z"] - 0.0006) / 2),
                  material="body_black")
        # The top print under the pack's opening, its picture centred under the mirror.
        parts.box("film_sheet", (0.079, 0.077, 0.0004), location=(0, ym, zf - 0.0004), material="lens_glass")
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


def drive(E):
    r, zf, pk, m = E["rollers"], E["film_plane_z"], E["pack"], E["motor"]
    ru, rl = r["upper_d"] / 2, r["lower_d"] / 2
    with parts.assembly("rollers", internal=True):
        ccyl("upper_roller", ru, r["length"], location=(0, r["y"], zf + ru), direction=(1, 0, 0),
                       material="roller_gold", segments=24)
        ccyl("lower_roller", rl, r["length"], location=(0, r["y"], zf - rl), direction=(1, 0, 0),
                       material="roller_steel", segments=24)
        for sgn in (1, -1):
            parts.box(f"roller_bracket_{'p' if sgn > 0 else 'm'}", (0.001, 0.014, 0.016),
                      location=(sgn * (r["length"] / 2 + 0.001), r["y"], zf), material="frame_steel")
    with parts.assembly("pick", internal=True):
        parts.box("pick_plate", (0.008, 0.07, 0.0004), location=(0.040, pk["front_y"] - 0.045, zf + 0.0006),
                  material="pick_brass")
    mx, my, mz = 0.026, 0.010, 0.036   # estimate: under the lens, beside the light cone
    gx = r["length"] / 2 + 0.003
    with parts.assembly("motor", internal=True):
        ccyl("motor_can", m["d"] / 2, m["length"], location=(mx, my, mz), direction=(1, 0, 0),
                       material="foil_silver", segments=24)
        ccyl("motor_pinion", 0.002, gx - mx - m["length"] / 2 + 0.001,
                       location=((mx + m["length"] / 2 + gx) / 2, my, mz), direction=(1, 0, 0),
                       material="pick_brass", segments=12)
    with parts.assembly("gear_train", internal=True):
        # Pinion -> four idlers -> the roller's gear, in the plane x = gx (layout estimated).
        a, b = Vector((my, mz)), Vector((r["y"], zf + ru))
        r0, r_end, n = 0.002, 0.006, 4
        dist = (b - a).length
        ri = (dist - r0 - r_end) / (2 * n)
        for k in range(n + 1):
            rr = ri if k < n else r_end
            cc = a + (b - a) * ((r0 + (2 * k + 1) * ri) / dist) if k < n else b
            gear(f"gear_{k}", rr, 0.0015, (gx, cc.x, cc.y), "body_black" if k < n else "roller_gold")
    with parts.assembly("wiring", internal=True):
        z0 = zf - pk["z"]
        for k, (sgn, mat) in enumerate(((1, "button_red"), (-1, "body_black"))):
            x = sgn * 0.012
            pts = [(x, pk["front_y"] - 0.004, z0 - 0.0006), (0.044, pk["front_y"] - 0.004 - 0.002 * k, z0 - 0.0006),
                   (0.046, pk["front_y"] - 0.006 - 0.002 * k, zf + 0.006), (0.046, my + 0.004, mz - 0.004),
                   (mx + 0.004 * sgn, my, mz - m["d"] / 2 - 0.0005)]
            parts.tube(f"wire_{k}", pts, 0.0005, segments=8, bend_radius=0.002, material=mat)


def viewfinder_optics(P):
    vw = P["viewfinder_window"]
    y_front = P["front_plate"]["y"] - 0.004
    y_back = P["lower_box"]["y0"] + 0.006
    with parts.assembly("viewfinder_optics", internal=True):
        parts.box("finder_tube", (0.020, y_front - y_back, 0.016), location=(vw["x"], (y_front + y_back) / 2, vw["z"] + 0.004),
                  material="lightbox_black")
        parts.box("eyepiece_lens", (0.016, 0.002, 0.013), location=(vw["x"], y_back - 0.001, vw["z"] + 0.005),
                  material="lens_glass")


SPEC = [None]


def build(spec):
    SPEC[0] = spec
    P = {k: v["value"] for k, v in spec["from_photos"].items()}
    E = {k: v["value"] for k, v in spec["estimates"].items() if isinstance(v, dict)}
    shell(P)
    front_parts(P)
    viewfinder_hood(P)
    ym = optics(P, E)
    film(E, ym)
    drive(E)
    viewfinder_optics(P)
    # The spec's positions are in the camera's own frame (lens along +y, button on +x). Turn the
    # whole model 180 degrees about z so it faces the viewer's front (-y, as Perseverance's).
    turn = Matrix.Rotation(math.pi, 4, "Z")
    for obj in parts.collection().objects:
        if obj.parent is None:
            obj.matrix_world = turn @ obj.matrix_world
