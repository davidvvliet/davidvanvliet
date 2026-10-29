# Blender side of build.py: KiCad's GLB in, the web model out.
#   Blender -b --python pack.py -- raw.glb blocks.json out.glb
# Every part goes under an empty named after its block (glTF extras "assembly", the board "core"),
# which the /models viewer uses to focus and explode. KiCad writes each track and pad as its own
# piece; merging each block into one mesh per material keeps the page fast.
import bpy, bmesh, json, sys, math
from mathutils import Vector

raw, tags, out = sys.argv[sys.argv.index("--") + 1:]
blocks = json.load(open(tags))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=raw)

def ref_of(o):
    while o:
        name = o.name.split(".")[0]
        if name in blocks or (o.type == "EMPTY" and name and not name.startswith("=>") and o.parent and o.parent.parent is None):
            return name
        o = o.parent
    return None

groups = {}
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    ref = ref_of(o)
    block = "Board" if ref is None else blocks.get(ref, "Other parts")
    groups.setdefault(block, []).append((o, ref))

placed = sorted({r for v in groups.values() for _, r in v if r})
mat_key = {}
MASK_ALPHA = 0.95
MASK_SPECULAR = 0.1  # Principled default 0.5
def canonical(m):
    if m is None: return None
    b = m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
    # The solder mask (KiCad: see-through, 0.8 to 0.83, coloured; the silkscreen is see-through white): more
    # opaque, or the shiny copper under it reflects the viewer's bright overhead light through it and washes
    # the colour out (a black mask looked beige). At 0.95 the traces still show faintly, as on a real board.
    if b and 0.5 < b.inputs["Alpha"].default_value < MASK_ALPHA and max(b.inputs["Base Color"].default_value[:3]) < 0.9:
        b.inputs["Alpha"].default_value = MASK_ALPHA
        # Less sheen too (exported as KHR_materials_specular): a flat board faces the viewer's big overhead
        # panel, and its reflection at the default level turned a black mask mid grey and hid the traces.
        b.inputs["Specular IOR Level"].default_value = MASK_SPECULAR
    k = tuple(round(x, 3) for x in b.inputs["Base Color"].default_value) + (round(b.inputs["Metallic"].default_value, 2),
         round(b.inputs["Roughness"].default_value, 2), round(b.inputs["Alpha"].default_value, 2)) if b else (m.name,)
    return mat_key.setdefault(k, m)

joined = {}
for block, items in groups.items():
    objs = [o for o, _ in items]
    for o in objs:
        o.data = o.data.copy()  # instances share meshes; joining needs their own
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = block
    # One slot per distinct material (KiCad gives each piece its own copy).
    # The exporter writes one primitive per distinct material, so equal slots merge there.
    me = o.data
    for i, s in enumerate(o.material_slots):
        me.materials[i] = canonical(s.material)
    # Merge the pieces' shared corners, then let flat copper and mask keep only the triangles they need.
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    if block == "Board":
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts, edges=bm.edges, use_dissolve_boundaries=False,
                                 delimit={"MATERIAL"})
    bm.to_mesh(me); bm.free()
    joined[block] = o

# Board centre at the origin.
board = joined["Board"]
pts = [board.matrix_world @ Vector(c) for c in board.bound_box]
mid = sum(pts, Vector()) / 8
for o in joined.values(): o.location -= Vector((mid.x, mid.y, min(p.z for p in pts)))

for block, o in joined.items():
    e = bpy.data.objects.new(f"block {block}", None); bpy.context.scene.collection.objects.link(e)
    e["assembly"] = block
    if block == "Board": e["core"] = True
    o.parent = e
for o in bpy.data.objects: o.select_set(o.name in joined or o.name.startswith("block "))
for o in [o for o in bpy.data.objects if not o.select_get()]: bpy.data.objects.remove(o)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_extras=True,
                          export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=10,
                          export_draco_position_quantization=16, export_draco_normal_quantization=10)
tris = {b: sum(len(p.vertices) - 2 for p in o.data.polygons) for b, o in joined.items()}
print("PACK " + json.dumps({"placed": placed, "tris": tris}))
