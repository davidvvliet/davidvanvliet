# Shared spacecraft parts. Every part is one mesh object in the "Probe" collection,
# built with bmesh (no operators, so it works headless and in the live session alike).
# Units are metres. A part's local +Z is its axis: `direction` aims it, `location` is
# its base (dish vertex, boom root, cylinder bottom).
import math
import bmesh, bpy
from mathutils import Matrix, Vector

from . import materials

COLLECTION = "Probe"

def collection():
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(col)
    return col

def clear():
    """Delete every object in the Probe collection (the rest of the scene is left alone)."""
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
    if material:
        mesh.materials.append(materials.get(material))
    obj = bpy.data.objects.new(name, mesh)
    collection().objects.link(obj)
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
             material="dark_metal", parent=None):
    bm = bmesh.new()
    _cyl(bm, radius, length, segments)
    return _object(name, bm, material, frame(location, direction), parent, smooth=True)

def prism(name, sides, radius, height, location=(0, 0, 0), direction=(0, 0, 1), roll_deg=0.0,
          material="foil_gold", parent=None):
    """Polygonal bus (Voyager's is a decagon). `radius` is to the corners."""
    bm = bmesh.new()
    _cyl(bm, radius, height, sides)
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
    return _object(name, bm, material, frame(location, direction), parent, smooth=True)

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
        material="dark_metal", parent=None):
    """Radioisotope generator: a cylinder with radial cooling fins. `fin_span` is the
    overall fin tip-to-tip diameter (default 2.2x the body)."""
    fin_span = fin_span or radius * 4.4
    fin_len = fin_span / 2 - radius
    bm = bmesh.new()
    _cyl(bm, radius, length, 24)
    for k in range(fins):
        a = 2 * math.pi * k / fins
        m = Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((radius + fin_len / 2, 0, length / 2))
        _box(bm, (fin_len, max(radius * 0.08, 0.004), length * 0.96), m)
    return _object(name, bm, material, frame(location, direction), parent)

def panel(name, width, height, thickness=0.03, location=(0, 0, 0), direction=(0, 0, 1),
          roll_deg=0.0, material="solar_cell", parent=None):
    """Flat panel (solar array, radiator) centred on `location`, facing `direction`."""
    return box(name, (width, height, thickness), location, direction, roll_deg, material, parent)
