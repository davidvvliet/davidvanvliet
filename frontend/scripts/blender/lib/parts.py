# Shared spacecraft parts. Every part is one mesh object in the "Probe" collection,
# built with bmesh (no operators, so it works headless and in the live session alike).
# Units are metres. A part's local +Z is its axis: `direction` aims it, `location` is
# its base (dish vertex, boom root, cylinder bottom).
import contextlib, math
import bmesh, bpy
from mathutils import Matrix, Vector

from . import materials

COLLECTION = "Probe"

# Assemblies: parts built inside `with assembly("wheel_lf"):` are tagged with that name (an
# object property, exported to glTF as node extras). Explode, the breakdown and the
# dashboard group by it; untagged parts fall back to their name (rtg_1 -> rtg).
_ASSEMBLY = [None]
_CORE = set()

@contextlib.contextmanager
def assembly(name, core=False):
    """Tag every part made inside the block. `core`: the assembly explode pushes away from
    (a bus or rover body); without one, a part named "bus" is the core."""
    prev = _ASSEMBLY[0]
    _ASSEMBLY[0] = name
    if core:
        _CORE.add(name)
    try:
        yield
    finally:
        _ASSEMBLY[0] = prev

def _tag(obj):
    if _ASSEMBLY[0]:
        obj["assembly"] = _ASSEMBLY[0]
        if _ASSEMBLY[0] in _CORE:
            obj["core"] = True

def collection():
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(col)
    return col

def clear():
    """Delete every object in the Probe collection (the rest of the scene is left alone)."""
    _CORE.clear()
    _ASSEMBLY[0] = None
    for obj in list(collection().objects):
        mesh = obj.data
        bpy.data.objects.remove(obj)
        if isinstance(mesh, bpy.types.Mesh) and mesh.users == 0:
            bpy.data.meshes.remove(mesh)

def frame(location=(0, 0, 0), direction=(0, 0, 1), roll_deg=0.0):
    """World matrix whose local +Z points along `direction`, rolled about it by `roll_deg`."""
    d = Vector(direction).normalized()
    rot = Vector((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()
    return Matrix.Translation(Vector(location)) @ rot @ Matrix.Rotation(math.radians(roll_deg), 4, "Z")

def _object(name, bm, material, matrix, parent=None, smooth=False):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.shade_smooth()
    # `material`: a palette name, a bpy Material, or a list of either (face material_index
    # picks from the list).
    for m in (material if isinstance(material, (list, tuple)) else [material] if material else []):
        mesh.materials.append(m if isinstance(m, bpy.types.Material) else materials.get(m))
    obj = bpy.data.objects.new(name, mesh)
    collection().objects.link(obj)
    _tag(obj)
    obj.matrix_world = matrix
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj

def _cyl(bm, radius, length, segments, matrix=Matrix(), cap=True):
    # create_cone centres the cylinder on its origin: shift it to sit on z = 0.
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=segments, radius1=radius, radius2=radius,
                          depth=length, matrix=matrix @ Matrix.Translation((0, 0, length / 2)))

def _box(bm, size, matrix=Matrix()):
    bmesh.ops.create_cube(bm, size=1.0, matrix=matrix @ Matrix.Diagonal((*size, 1.0)))

def cylinder(name, radius, length, location=(0, 0, 0), direction=(0, 0, 1), segments=32,
             material="dark_metal", parent=None, caps=True):
    """`caps=False`: an open tube (a camera's sunshade)."""
    bm = bmesh.new()
    _cyl(bm, radius, length, segments, cap=caps)
    return _object(name, bm, material, frame(location, direction), parent, smooth=True)

def prism(name, sides, radius, height, location=(0, 0, 0), direction=(0, 0, 1), roll_deg=0.0,
          material="foil_gold", parent=None, cap_top=True):
    """Polygonal bus (Voyager's is a decagon). `radius` is to the corners. `cap_top=False`
    leaves the top open (a band under a dish, whose middle sits lower than the band's edge)."""
    bm = bmesh.new()
    _cyl(bm, radius, height, sides)
    if not cap_top:
        bm.normal_update()
        top = max(bm.faces, key=lambda f: f.calc_center_median().z)
        bmesh.ops.delete(bm, geom=[top], context="FACES_ONLY")
    return _object(name, bm, material, frame(location, direction, roll_deg), parent)

def box(name, size, location=(0, 0, 0), direction=(0, 0, 1), roll_deg=0.0,
        material="foil_gold", parent=None):
    """Box of `size` (x, y, z) centred on `location`."""
    bm = bmesh.new()
    _box(bm, size)
    return _object(name, bm, material, frame(location, direction, roll_deg), parent)

def dish(name, diameter, depth, location=(0, 0, 0), direction=(0, 0, 1), thickness=0.02,
         rings=12, segments=48, material="white_paint", parent=None):
    """Parabolic reflector: vertex at `location`, opening toward `direction`.
    `depth` is rim height above the vertex (focal length f = D^2 / (16 depth))."""
    r_max = diameter / 2
    f = diameter ** 2 / (16 * depth)
    bm = bmesh.new()
    rows = []
    for i in range(rings + 1):
        r = r_max * i / rings
        z = r * r / (4 * f)
        if i == 0:
            rows.append([bm.verts.new((0, 0, z))])
            continue
        rows.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                     for a in (2 * math.pi * k / segments for k in range(segments))])
    for i in range(1, len(rows)):
        inner, outer = rows[i - 1], rows[i]
        for k in range(segments):
            k2 = (k + 1) % segments
            if len(inner) == 1:
                bm.faces.new((inner[0], outer[k], outer[k2]))
            else:
                bm.faces.new((inner[k], outer[k], outer[k2], inner[k2]))
    # Give the shell its thickness in the mesh itself, so measurements and exports agree.
    bm.normal_update()
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thickness)
    return _object(name, _ordered(bm), material, frame(location, direction), parent, smooth=True)

def _ordered(bm):
    """The same mesh with vertices and faces in a fixed order (solidify's order changes from
    run to run, and the baked atlas's layout depends on it). Each face keeps its winding and
    starts at its lowest vertex."""
    key = lambda co: (round(co.x, 6), round(co.y, 6), round(co.z, 6))
    verts = sorted({key(v.co) for v in bm.verts})
    index = {k: i for i, k in enumerate(verts)}
    faces = []
    for f in bm.faces:
        ids = [index[key(v.co)] for v in f.verts]
        s = ids.index(min(ids))
        faces.append(tuple(ids[s:] + ids[:s]))
    bm.free()
    out = bmesh.new()
    vs = [out.verts.new(k) for k in verts]
    for ids in sorted(faces):
        out.faces.new([vs[i] for i in ids])
    return out

def boom(name, length, width, location=(0, 0, 0), direction=(1, 0, 0), truss=True, bays=None,
         rod=None, material="dark_metal", parent=None):
    """Instrument or RTG boom. A truss is three longerons with diagonals, `width` across;
    otherwise a solid rod of diameter `width`."""
    bm = bmesh.new()
    if not truss:
        _cyl(bm, width / 2, length, 12)
    else:
        rod = rod or max(width * 0.06, 0.004)
        bays = bays or max(1, round(length / width))
        R = width / math.sqrt(3)  # circumradius of the triangle
        corners = [Vector((R * math.cos(a), R * math.sin(a), 0))
                   for a in (math.radians(90 + 120 * k) for k in range(3))]
        def bar(p, q):
            d = q - p
            m = Matrix.Translation(p) @ Vector((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()
            _cyl(bm, rod / 2, d.length, 6, m, cap=False)
        step = length / bays
        for c in corners:
            bar(c, c + Vector((0, 0, length)))
        for b in range(bays):
            z0, z1 = b * step, (b + 1) * step
            for k in range(3):
                a, n = corners[k], corners[(k + 1) % 3]
                bar(a + Vector((0, 0, z0)), n + Vector((0, 0, z1)))       # diagonal
                bar(a + Vector((0, 0, z1)), n + Vector((0, 0, z1)))       # batten
    return _object(name, bm, material, frame(location, direction), parent)

def rtg(name, length, radius, fins=6, fin_span=None, location=(0, 0, 0), direction=(0, 0, 1),
        material="dark_metal", parent=None, separate_fins=False):
    """Radioisotope generator: a cylinder with radial cooling fins. `fin_span` is the
    overall fin tip-to-tip diameter (default 2.2x the body). With `separate_fins` the fins
    are their own object, `<name>_fins`, so the body can be checked on its own."""
    fin_span = fin_span or radius * 4.4
    fin_len = fin_span / 2 - radius
    bm = bmesh.new()
    _cyl(bm, radius, length, 24)
    fb = bmesh.new() if separate_fins else bm
    for k in range(fins):
        a = 2 * math.pi * k / fins
        m = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((radius + fin_len / 2, 0, length / 2))
        _box(fb, (fin_len, max(radius * 0.08, 0.004), length * 0.96), m)
    body = _object(name, bm, material, frame(location, direction), parent)
    if separate_fins:
        _object(f"{name}_fins", fb, material, frame(location, direction), parent)
    return body

def panel(name, width, height, thickness=0.03, location=(0, 0, 0), direction=(0, 0, 1),
          roll_deg=0.0, material="solar_cell", parent=None):
    """Flat panel (solar array, radiator) centred on `location`, facing `direction`."""
    return box(name, (width, height, thickness), location, direction, roll_deg, material, parent)

def strut(name, start, end, radius=0.012, segments=8, material="dark_metal", parent=None):
    """A straight rod from `start` to `end` (struts, legs, rails)."""
    a, b = Vector(start), Vector(end)
    return cylinder(name, radius, (b - a).length, location=a, direction=b - a, segments=segments,
                    material=material, parent=parent)

def disc(name, radius, thickness, location=(0, 0, 0), direction=(0, 0, 1), roll_deg=0.0,
         segments=96, bevel=0.001, hub=None, material="foil_gold", hole_material="black", parent=None):
    """Thin plate (plaque, record cover): back face at `location`, front face `thickness` out
    along `direction`, front rim chamfered by `bevel`. The front face is UV-mapped onto the
    square [0, 1]^2 (circle inscribed, +v = the plate's local +y, turned by `roll_deg`), so a
    square image of the face maps straight on; rim and back use the image's corner.
    `hub`: {"outer": r, "inner": r, "height": h}, a raised ring at the centre with a hole
    (`hole_material`) through the plate."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    corner = (0.01, 0.01)
    def ring(r, z):
        return [bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                for a in (2 * math.pi * k / segments for k in range(segments))]
    back = ring(radius, 0.0)
    rim = ring(radius, thickness - bevel)
    front = ring(radius - bevel, thickness)
    if hub:  # the back as an annulus around the hole
        back_in = ring(hub["inner"], 0.0)
        faces = [bm.faces.new((back[(k + 1) % segments], back[k], back_in[k], back_in[(k + 1) % segments]))
                 for k in range(segments)]
    else:
        faces = [bm.faces.new(list(reversed(back)))]
    for a, b in ((back, rim), (rim, front)):
        for k in range(segments):
            k2 = (k + 1) % segments
            faces.append(bm.faces.new((a[k], a[k2], b[k2], b[k])))
    def face_uv(f):
        for loop in f.loops:
            x, y = loop.vert.co.x, loop.vert.co.y
            loop[uv].uv = (0.5 + x / (2 * radius), 0.5 + y / (2 * radius))
    if hub:
        # Front face as an annulus around the hub; the hub ring, its top, its hole wall and floor.
        ro, ri, hh = hub["outer"], hub["inner"], hub["height"]
        h_base = ring(ro, thickness)
        for k in range(segments):
            k2 = (k + 1) % segments
            face_uv(bm.faces.new((front[k], front[k2], h_base[k2], h_base[k])))
        h_top = ring(ro, thickness + hh)
        h_in = ring(ri, thickness + hh)
        h_floor = ring(ri, thickness)
        for a, b in ((h_base, h_top), (h_top, h_in), (h_in, h_floor)):
            for k in range(segments):
                k2 = (k + 1) % segments
                face_uv(bm.faces.new((a[k], a[k2], b[k2], b[k])))
        for k in range(segments):  # the hole's wall on down to the back
            k2 = (k + 1) % segments
            wall = bm.faces.new((h_floor[k], h_floor[k2], back_in[k2], back_in[k]))
            wall.material_index = 1
    else:
        face_uv(bm.faces.new(front))
    for f in faces:
        for loop in f.loops:
            loop[uv].uv = corner
    mats = [material, hole_material] if hub else material
    return _object(name, bm, mats, frame(location, direction, roll_deg), parent)

def plate(name, width, height, thickness, location=(0, 0, 0), direction=(0, 0, 1), up=(0, 0, 1),
          material="white_paint", parent=None):
    """Rectangular plate (placard, plaque, flag plate): back face centred on `location`, front
    face `thickness` out along `direction`. `up` is the in-plane direction of the image's top
    (projected onto the plate); `width` runs to the image's right. The front face is UV-mapped
    onto [0, 1]^2, so an image of the face maps straight on; edges and back use its corner."""
    n = Vector(direction).normalized()
    v = Vector(up) - n * Vector(up).dot(n)
    if v.length < 1e-6:
        raise ValueError(f"plate {name}: `up` is along the plate's normal")
    v.normalize()
    u = v.cross(n)                      # the image's right, seen from the front
    m = Matrix((u, v, n)).transposed().to_4x4()
    m.translation = Vector(location)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    w, h = width / 2, height / 2
    back = [bm.verts.new((x, y, 0.0)) for x, y in ((-w, -h), (w, -h), (w, h), (-w, h))]
    front = [bm.verts.new((x, y, thickness)) for x, y in ((-w, -h), (w, -h), (w, h), (-w, h))]
    face = bm.faces.new(front)
    for loop in face.loops:
        loop[uv].uv = (loop.vert.co.x / width + 0.5, loop.vert.co.y / height + 0.5)
    others = [bm.faces.new(list(reversed(back)))]
    for k in range(4):
        k2 = (k + 1) % 4
        others.append(bm.faces.new((back[k], back[k2], front[k2], front[k])))
    for f in others:
        for loop in f.loops:
            loop[uv].uv = (0.01, 0.01)
    return _object(name, bm, material, m, parent)

def outline_plate(name, outline, width, height, thickness, location=(0, 0, 0), direction=(0, 0, 1),
                  up=(0, 0, 1), side_uv=(0.5, 0.5), material="white_paint", parent=None):
    """A plate cut to a shape: `outline` is the plate's edge as (u, v) points in its image
    ([0, 1]^2, v up), scaled to `width` x `height`. Placed like `plate`; the front face shows
    the image, the edges and back take the colour at `side_uv` (a point on the plate)."""
    n = Vector(direction).normalized()
    v = Vector(up) - n * Vector(up).dot(n)
    if v.length < 1e-6:
        raise ValueError(f"outline_plate {name}: `up` is along the plate's normal")
    v.normalize()
    m = Matrix((v.cross(n), v, n)).transposed().to_4x4()
    m.translation = Vector(location)
    pts = [(u, w) for u, w in outline]
    # Counter-clockwise seen from the front, so the front face points along +z.
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) < 0:
        pts.reverse()
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    back = [bm.verts.new(((u - 0.5) * width, (w - 0.5) * height, 0.0)) for u, w in pts]
    front = [bm.verts.new(((u - 0.5) * width, (w - 0.5) * height, thickness)) for u, w in pts]
    face = bm.faces.new(front)
    for loop, (u, w) in zip(face.loops, pts):
        loop[uv].uv = (u, w)
    others = [bm.faces.new(list(reversed(back)))]
    k = len(pts)
    for i in range(k):
        j = (i + 1) % k
        others.append(bm.faces.new((back[i], back[j], front[j], front[i])))
    for f in others:
        for loop in f.loops:
            loop[uv].uv = side_uv
    # Concave outlines: split the two caps into triangles so every viewer draws them right.
    bmesh.ops.triangulate(bm, faces=[face, others[0]])
    return _object(name, bm, material, m, parent)

def meshes(objs):
    """The mesh parts among `objs` (joints are empties)."""
    return [o for o in objs if o.type == "MESH"]

# --- Joints -------------------------------------------------------------------------
# A joint is an empty at a pivot. Build every part unposed (in world coordinates) with
# `parent=joint`, then call pose() once at the end: rotating a joint carries everything
# parented to it, through any depth of joints.

def joint(name, location, axis=(1, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.1
    collection().objects.link(obj)
    _tag(obj)
    obj.matrix_world = Matrix.Translation(Vector(location))
    obj["joint_axis"] = list(Vector(axis).normalized())
    obj["angle_deg"] = 0.0
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    obj["rest_location"] = list(obj.matrix_basis.translation)  # pose() turns from here
    return obj

def pose(angles):
    """Turn joints by name: {"arm_shoulder": 30, ...} (degrees about each joint's axis, in
    the unposed frame). Angles are absolute: posing again replaces the earlier angle. Call
    after every part is built."""
    for name, deg in angles.items():
        obj = bpy.data.objects.get(name)
        if obj is None or "joint_axis" not in obj:
            raise KeyError(f"pose: no joint named {name}")
        obj["angle_deg"] = float(deg)
        rot = Matrix.Rotation(math.radians(deg), 4, Vector(obj["joint_axis"]))
        obj.matrix_basis = Matrix.Translation(Vector(obj["rest_location"])) @ rot
    bpy.context.view_layer.update()

def chain(name, base, direction, links, parent=None, material="dark_metal"):
    """Arm or mast: links end to end along `direction`, each starting at a joint.
    `links`: [{"length": m, "radius": m, "axis": (x, y, z)}]. Joints are named
    <name>_j1, <name>_j2, ...; links <name>_1, ... Returns the joints (pose them by name)."""
    d = Vector(direction).normalized()
    p = Vector(base)
    joints = []
    for i, link in enumerate(links, 1):
        j = joint(f"{name}_j{i}", p, link.get("axis", (1, 0, 0)), parent=joints[-1] if joints else parent)
        cylinder(f"{name}_{i}", link["radius"], link["length"], location=p, direction=d, segments=16,
                 material=link.get("material", material), parent=j)
        joints.append(j)
        p = p + d * link["length"]
    return joints

def sides():
    """(sign, tag) for a left/right pair: build one side as a function of `sign` and call it
    for each. Which world axis is lateral is the probe's frame (see its spec)."""
    return ((1, "left"), (-1, "right"))

# --- Shapes ---------------------------------------------------------------------------

def _lathe(bm, profile, segments, matrix=Matrix()):
    """Spin a profile [(r, z), ...] about local Z. Points with r == 0 become poles. Give the
    profile going up the outside of the shape so faces point outward."""
    rings = []
    for r, z in profile:
        if r <= 1e-9:
            rings.append([bm.verts.new(matrix @ Vector((0, 0, z)))])
        else:
            rings.append([bm.verts.new(matrix @ Vector((r * math.cos(a), r * math.sin(a), z)))
                          for a in (2 * math.pi * k / segments for k in range(segments))])
    for a, b in zip(rings, rings[1:]):
        for k in range(segments):
            k2 = (k + 1) % segments
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[k2], b[k]))
            elif len(b) == 1:
                bm.faces.new((a[k], a[k2], b[0]))
            else:
                bm.faces.new((a[k], a[k2], b[k2], b[k]))
    return rings

def lathe(name, profile, location=(0, 0, 0), direction=(0, 0, 1), segments=48, closed=False,
          material="white_paint", smooth=True, parent=None):
    """Body of revolution (capsule, heat shield, nozzle, tank, wheel hub, camera head): the
    profile [(r, z), ...] spun about `direction` from `location`. Start and end on the axis
    (r = 0) for a closed solid, or pass `closed=True` to join the last point back to the first
    (a ring section, e.g. a tyre)."""
    bm = bmesh.new()
    pts = list(profile) + ([profile[0]] if closed else [])
    _lathe(bm, pts, segments)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    return _object(name, bm, material, frame(location, direction), parent, smooth=smooth)

def wheel(name, diameter, width, location=(0, 0, 0), axle=(1, 0, 0), rim=None, cleats=0,
          cleat_height=0.0, cleat_width=0.01, spokes=0, spoke_width=None, hub_diameter=None,
          segments=64, material="dark_metal", parent=None):
    """Wheel centred on `location`, turning about `axle`: a tyre ring `rim` thick (default 4%
    of the diameter), straight cleats across the tread, spokes from the hub to the rim."""
    R, w = diameter / 2, width
    t = rim if rim is not None else diameter * 0.04
    bm = bmesh.new()
    _lathe(bm, [(R - t, -w / 2), (R, -w / 2), (R, w / 2), (R - t, w / 2), (R - t, -w / 2)], segments)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    for i in range(cleats):
        a = 2 * math.pi * i / cleats
        m = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((R + cleat_height / 2, 0, 0))
        _box(bm, (cleat_height, cleat_width, w), m)
    hub_r = (hub_diameter or diameter * 0.2) / 2
    if spokes:
        _cyl(bm, hub_r, w * 0.8, 24, Matrix.Translation((0, 0, -w * 0.4)))
        sw = spoke_width or diameter * 0.03
        for i in range(spokes):
            a = 2 * math.pi * i / spokes
            m = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation(((hub_r + R - t) / 2, 0, 0))
            _box(bm, (R - t - hub_r + 0.002, sw, sw * 0.5), m)
    return _object(name, bm, material, frame(location, axle), parent)

def _round_corners(points, radius, steps=6):
    """Replace each interior corner of a polyline by a quadratic bend of about `radius`."""
    if radius <= 0 or len(points) < 3:
        return points
    out = [points[0]]
    for a, b, c in zip(points, points[1:], points[2:]):
        u, v = (a - b), (c - b)
        r = min(radius, u.length / 2, v.length / 2)
        p, q = b + u.normalized() * r, b + v.normalized() * r
        for i in range(steps + 1):
            t = i / steps
            out.append(p * (1 - t) ** 2 + b * 2 * t * (1 - t) + q * t * t)
    out.append(points[-1])
    return out

def tube(name, points, radius, segments=12, bend_radius=0.0, material="dark_metal", parent=None):
    """A tube through `points` (rover suspension arms, handrails, cables), corners bent with
    `bend_radius`, ends capped."""
    pts = _round_corners([Vector(p) for p in points], bend_radius)
    bm = bmesh.new()
    # Parallel-transport a ring frame along the path, mitred at each point.
    tangents = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        tangents.append((b - a).normalized())
    n = tangents[0].orthogonal().normalized()
    rings = []
    for i, (p, t) in enumerate(zip(pts, tangents)):
        if i:
            n = (n - t * n.dot(t)).normalized()
        b = t.cross(n)
        rings.append([bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * radius)
                      for a in (2 * math.pi * k / segments for k in range(segments))])
    for a, c in zip(rings, rings[1:]):
        for k in range(segments):
            k2 = (k + 1) % segments
            bm.faces.new((a[k], a[k2], c[k2], c[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return _object(name, bm, material, Matrix(), parent, smooth=True)
