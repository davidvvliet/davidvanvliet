# Shared parts, the core: the collection every part goes in, assemblies, the one place a
# bmesh becomes an object (_object), joints and poses. Imported through lib/parts.py.
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

def sides():
    """(sign, tag) for a left/right pair: build one side as a function of `sign` and call it
    for each. Which world axis is lateral is the probe's frame (see its spec)."""
    return ((1, "left"), (-1, "right"))

