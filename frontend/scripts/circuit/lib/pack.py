# Blender side of build.py: KiCad's GLB in, the web model out.
#   Blender -b --python pack.py -- raw.glb blocks.json out.glb [top|back] [screens.json]
# Every part goes under an empty named after its block (glTF extras "assembly", the board "core"),
# which the /models viewer uses to focus and explode. KiCad writes each track and pad as its own
# piece; merging each block into one mesh per material keeps the page fast.
import bpy, bmesh, json, sys, math
from mathutils import Vector

raw, tags, out, *rest = sys.argv[sys.argv.index("--") + 1:]
view = rest[0] if rest else "top"
screens = json.load(open(rest[1])) if len(rest) > 1 else []
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
MASK_SPECULAR = 0.1  # Principled default 0.5
COPPER_METALLIC, COPPER_ROUGHNESS = 0.2, 0.6  # KiCad's copper: 1.0 and 0.4
def canonical(m, board=False):
    if m is None: return None
    b = m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
    # The solder mask stays as see-through as KiCad draws it (0.8 to 0.83, coloured; the silkscreen is
    # see-through white), with less sheen (exported as KHR_materials_specular): a flat board faces the
    # viewer's big overhead panel, and its reflection at the default level turned a black mask grey.
    if b and 0.5 < b.inputs["Alpha"].default_value < 1 and max(b.inputs["Base Color"].default_value[:3]) < 0.9:
        b.inputs["Specular IOR Level"].default_value = MASK_SPECULAR
    # The board's copper is matte: shiny copper under the see-through mask mirrored that overhead panel
    # through it and washed the mask's colour out (black looked beige). Parts keep their metal.
    if board and b and b.inputs["Metallic"].default_value > 0.5:
        m = m.copy()
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Metallic"].default_value = COPPER_METALLIC
        b.inputs["Roughness"].default_value = COPPER_ROUGHNESS
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
        me.materials[i] = canonical(s.material, block == "Board")
    # Merge the pieces' shared corners, then let flat copper and mask keep only the triangles they need.
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    if block == "Board":
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts, edges=bm.edges, use_dissolve_boundaries=False,
                                 delimit={"MATERIAL"})
    bm.to_mesh(me); bm.free()
    joined[block] = o

# A board whose screen is on its back is shown back up (recipe "view": "back"): turned over about its long axis.
if view == "back":
    from mathutils import Matrix
    for o in joined.values(): o.matrix_world = Matrix.Rotation(math.pi, 4, "X") @ o.matrix_world

# Board centre at the origin.
board = joined["Board"]
pts = [board.matrix_world @ Vector(c) for c in board.bound_box]
mid = sum(pts, Vector()) / 8
for o in joined.values(): o.location -= Vector((mid.x, mid.y, min(p.z for p in pts)))

# Screens on (recipe "screens"): the faces of a block in the display area's colour (its model's, as KiCad exports it:
# linear) show an image, mapped flat across them, turned by "rotate" degrees; "glow" lights it (a backlit LCD).
bpy.context.view_layer.update()
for s in screens:
    o = joined.get(s["block"])
    if o is None: sys.exit(f"screen: no block {s['block']!r}")
    me = o.data
    hit = {i for i, sl in enumerate(o.material_slots) if sl.material and sl.material.use_nodes and
           all(abs(a - b) <= s.get("tolerance", 0.01) for a, b in
               zip(sl.material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value[:3], s["color"]))}
    polys = [p for p in me.polygons if p.material_index in hit]
    if not polys: sys.exit(f"screen: no faces of colour {s['color']} in {s['block']!r}")
    img = bpy.data.images.load(s["image"]); img.pack()
    m = bpy.data.materials.new(f"screen {s['block']}"); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = s.get("roughness", 0.5); b.inputs["Metallic"].default_value = 0
    if s.get("glow"):
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = s["glow"]
    me.materials.append(m); k = len(me.materials) - 1
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    mw = o.matrix_world
    pts = [mw @ me.vertices[v].co for p in polys for v in p.vertices]
    x0, x1 = min(q.x for q in pts), max(q.x for q in pts); y0, y1 = min(q.y for q in pts), max(q.y for q in pts)
    turn = round(s.get("rotate", 0) / 90) % 4
    for p in polys:
        p.material_index = k
        for li in p.loop_indices:
            q = mw @ me.vertices[me.loops[li].vertex_index].co
            u, v = (q.x - x0) / (x1 - x0), (q.y - y0) / (y1 - y0)
            for _ in range(turn): u, v = v, 1 - u
            uv.data[li].uv = (u, v)

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
