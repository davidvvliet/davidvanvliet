# Baked colour: one atlas image for a whole probe, its colours projected from a reference
# model (`run.py bake`), applied on every build. The atlas layout comes from unwrapping the
# probe's parts together the same way each time, so a build reproduces the UVs the atlas was
# baked for; a fingerprint of the geometry tells a build when the atlas is stale.
# Parts that carry their own image (plates, engravings) keep it and are left out.
import hashlib, json, os
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

UV = "bake"
HIDDEN_SCALE = 0.05    # texel density of hidden faces relative to visible ones
HIDDEN_GAP = 0.01      # m: a face whose sample rays all hit something this close is hidden
HIDDEN_FOLD = 0.003    # m: back faces this close are the face's own fold (a bent quad), not a part
                       # around it. unwrap(fold=HIDDEN_FOLD) uses it (the livery); 0 keeps older bakes' layouts
STATS = {}             # last unwrap: faces, hidden

def _textured(o):
    return any(n.type == "TEX_IMAGE" for m in o.data.materials if m and m.node_tree for n in m.node_tree.nodes)

def _joints():
    from lib import parts
    return [o for o in parts.collection().objects if "joint_axis" in o]

class at_rest:
    """Joints at 0 (the reference model's pose) inside the block, back as posed after: the
    atlas and fingerprint don't depend on the pose, so turning a joint needs no re-bake."""
    def __enter__(self):
        from lib import parts
        self.angles = {o.name: o["angle_deg"] for o in _joints()}
        parts.pose({n: 0.0 for n in self.angles})
    def __exit__(self, *exc):
        from lib import parts
        parts.pose(self.angles)

def targets(objs):
    """The parts the atlas covers: meshes without an image of their own, in name order."""
    return sorted((o for o in objs if o.type == "MESH" and not _textured(o) and o.data.polygons),
                  key=lambda o: o.name)

def fingerprint(objs):
    """Hash of the parts' world-space geometry (rounded to 0.1 mm) and face layout."""
    h = hashlib.sha1()
    with at_rest():
        _hash(objs, h)
    return h.hexdigest()[:16]

def _hash(objs, h):
    for o in targets(objs):
        mw = np.array(o.matrix_world)
        co = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", co)
        p = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        h.update(o.name.encode())
        h.update(np.round(p * 1e4).astype(np.int64).tobytes())
        lt = np.empty(len(o.data.loops), dtype=np.int32)
        o.data.loops.foreach_get("vertex_index", lt)
        h.update(lt.tobytes())

def unwrap(objs, margin=0.001, fold=0.0):
    """Lay every target's faces out in one atlas (world scale, so texel size is even) and
    store it as each part's active UV map (laid out at rest). Faces nobody can see (covered
    by another part, or inside one) get a token corner. Returns the targets."""
    with at_rest():
        occluders = _occluders([o for o in objs if o.type == "MESH"])
        return _unwrap(targets(objs), margin, occluders, fold)

def _occluders(meshes):
    verts, polys = [], []
    for o in meshes:
        mw = o.matrix_world
        base = len(verts)
        verts.extend(mw @ v.co for v in o.data.vertices)
        polys.extend([base + i for i in p.vertices] for p in o.data.polygons)
    return BVHTree.FromPolygons(verts, polys)

def _hidden(me, tree, fold=0.0):
    """Per face of the world-space mesh `me`: True when every sample point's outward ray
    hits a front face within HIDDEN_GAP or the inside of a part (a back face, past the
    face's own fold)."""
    hidden = np.zeros(len(me.polygons), dtype=bool)
    co = [v.co for v in me.vertices]
    for p in me.polygons:
        n = p.normal
        c = p.center
        pts = [c] + [c.lerp(co[i], 0.7) for i in p.vertices]
        covered = True
        for q in pts:
            start = q + n * 1e-4
            loc, nrm, _, dist = tree.ray_cast(start, n, 0.5)
            while loc is not None and nrm.dot(n) >= 0 and (loc - q).length < fold:
                start = loc + n * 1e-4
                loc, nrm, _, dist = tree.ray_cast(start, n, 0.5)
            if loc is not None:
                dist = (loc - q).length
            if loc is None or (nrm.dot(n) < 0 and dist > HIDDEN_GAP):
                covered = False
                break
        hidden[p.index] = covered
    return hidden

def _density(me, faces, uv):
    """sqrt(UV area / world area) over `faces`."""
    a3 = a2 = 0.0
    for f in faces:
        p = me.polygons[f]
        a3 += p.area
        u = [uv[l] for l in p.loop_indices]
        a2 += abs(sum(u[i][0] * u[(i + 1) % len(u)][1] - u[(i + 1) % len(u)][0] * u[i][1] for i in range(len(u)))) / 2
    return (a2 / a3) ** 0.5 if a3 > 0 and a2 > 0 else 1.0

def _unwrap(objs, margin, occluders, fold=0.0):
    bpy.context.view_layer.update()
    # Work on a joined world-space copy; each face remembers its part and index.
    copies = []
    for i, o in enumerate(objs):
        me = o.data.copy()
        me.transform(o.matrix_world)
        n = len(me.polygons)
        me.attributes.new("src_obj", "INT", "FACE").data.foreach_set("value", np.full(n, i, dtype=np.int32))
        me.attributes.new("src_face", "INT", "FACE").data.foreach_set("value", np.arange(n, dtype=np.int32))
        c = bpy.data.objects.new(f"_uv_{i}", me)
        bpy.context.scene.collection.objects.link(c)
        copies.append(c)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    me = joined.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name=UV)
    hidden = _hidden(me, occluders, fold)
    # Visible and hidden faces are projected separately, so no island mixes them; hidden
    # islands are then shrunk before packing (packing keeps relative sizes).
    for group in (~hidden, hidden):
        if not group.any():
            continue
        me.polygons.foreach_set("select", group)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=margin, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    if hidden.any() and (~hidden).any():
        uv = np.empty(len(me.loops) * 2)
        me.uv_layers[UV].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        k = HIDDEN_SCALE * _density(me, np.nonzero(~hidden)[0], uv) / _density(me, np.nonzero(hidden)[0], uv)
        for f in np.nonzero(hidden)[0]:
            p = me.polygons[f]
            uv[p.loop_start:p.loop_start + p.loop_total] *= k
        me.uv_layers[UV].data.foreach_set("uv", uv.ravel())
    me.polygons.foreach_set("select", np.ones(len(me.polygons), dtype=bool))
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)  # fill the square
    bpy.ops.object.mode_set(mode="OBJECT")
    STATS.update(faces=len(me.polygons), hidden=int(hidden.sum()))
    # Copy the atlas back to each part, face by face (join keeps each polygon's loop order).
    n = len(me.polygons)
    so, sf = np.empty(n, dtype=np.int32), np.empty(n, dtype=np.int32)
    me.attributes["src_obj"].data.foreach_get("value", so)
    me.attributes["src_face"].data.foreach_get("value", sf)
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[UV].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    start = np.empty(n, dtype=np.int32)
    me.polygons.foreach_get("loop_start", start)
    total = np.empty(n, dtype=np.int32)
    me.polygons.foreach_get("loop_total", total)
    for i, o in enumerate(objs):
        d = o.data
        for other in [l for l in d.uv_layers if l.name != UV]:  # only the atlas is exported
            d.uv_layers.remove(other)
        layer = d.uv_layers.get(UV) or d.uv_layers.new(name=UV)
        d.uv_layers.active = layer
        out = np.zeros((len(d.loops), 2))
        ostart = np.empty(len(d.polygons), dtype=np.int32)
        d.polygons.foreach_get("loop_start", ostart)
        for f in np.nonzero(so == i)[0]:
            k = total[f]
            out[ostart[sf[f]]:ostart[sf[f]] + k] = uv[start[f]:start[f] + k]
        layer.data.foreach_set("uv", out.ravel())
    bpy.data.objects.remove(joined)
    bpy.data.meshes.remove(me)
    return objs

def layout(objs):
    """Hash of the atlas UVs of the targets (to 1e-5)."""
    h = hashlib.sha1()
    for o in targets(objs):
        uv = np.empty(len(o.data.loops) * 2)
        o.data.uv_layers[UV].data.foreach_get("uv", uv)
        h.update(o.name.encode())
        h.update(np.round(uv * 1e5).astype(np.int64).tobytes())
    return h.hexdigest()[:16]

def paths(harness, probe):
    d = os.path.join(harness, "refs", probe)
    return os.path.join(d, "baked.jpg"), os.path.join(d, "baked.json")

def normal_path(harness, probe):
    return os.path.join(harness, "refs", probe, "baked_normal.jpg")

def _load(path, colour=True):
    img = bpy.data.images.load(path, check_existing=True)
    img.reload()  # the live session keeps images between builds; the bake may have replaced it
    if not colour:
        img.colorspace_settings.name = "Non-Color"
    return img

def apply(objs, image_path, normal_path=None):
    """Give every target's materials the atlas as base colour, and the baked normal map if
    there is one (metal and roughness stay as sourced). Each material is copied once, shared
    by all targets that used it."""
    img = _load(image_path)
    nimg = _load(normal_path, colour=False) if normal_path and os.path.exists(normal_path) else None
    done = {}
    for o in targets(objs):
        for slot in o.material_slots:
            m = slot.material
            if m is None:
                continue
            if m.name not in done:
                b = m.copy()
                b.name = m.name + "_baked"
                nt = b.node_tree
                bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
                tex = nt.nodes.new("ShaderNodeTexImage")
                tex.image = img
                uvn = nt.nodes.new("ShaderNodeUVMap")
                uvn.uv_map = UV
                nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
                nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
                if nimg is not None:
                    ntex = nt.nodes.new("ShaderNodeTexImage")
                    ntex.image = nimg
                    nt.links.new(uvn.outputs["UV"], ntex.inputs["Vector"])
                    nmap = nt.nodes.new("ShaderNodeNormalMap")
                    nmap.uv_map = UV
                    nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
                    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
                done[m.name] = b
            slot.material = done[m.name]
    return img

def stale(objs, json_path):
    """None when the atlas was baked for this geometry, else why not."""
    try:
        info = json.load(open(json_path))
    except (OSError, ValueError):
        return "no baked.json"
    fp = fingerprint(objs)
    if info.get("fingerprint") != fp:
        return f"geometry changed since the bake ({info.get('fingerprint')} -> {fp}): run `run.py bake`"
    lay = layout(objs)
    if info.get("layout") != lay:
        return f"atlas layout differs from the bake's ({info.get('layout')} -> {lay})"
    return None

# --- Baking helpers (used by run.py bake and the livery step) ----------------------

def world_copy(objs, name):
    """One object joining world-space copies of `objs` (materials and UVs kept)."""
    copies = []
    for o in objs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        c = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(c)
        copies.append(c)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    if len(copies) > 1:
        bpy.ops.object.join()
    j = bpy.context.view_layer.objects.active
    j.name = name
    return j

def albedo(mats, on):
    """Switch materials to show their plain base colour (an emission of it) or back. A
    diffuse bake reads base colour x (1 - metallic) x (1 - transmission), so metal and glass
    would bake black; emission bakes the base colour itself, texture and all."""
    for m in mats:
        if not m or not m.node_tree:
            continue
        nt = m.node_tree
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if out is None or bsdf is None:
            continue
        if on:
            em = nt.nodes.get("_albedo") or nt.nodes.new("ShaderNodeEmission")
            em.name = "_albedo"
            src = bsdf.inputs["Base Color"]
            if src.is_linked:
                nt.links.new(src.links[0].from_socket, em.inputs["Color"])
            else:
                em.inputs["Color"].default_value = src.default_value
            nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
        else:
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

def bake_into(target, img, selected=(), extrusion=0.0, max_ray=0.0, kind="DIFFUSE"):
    """Bake the albedo seen by `target` (from `selected` when given) into `img`."""
    for m in target.data.materials:
        nt = m.node_tree
        node = next((n for n in nt.nodes if n.name == "_bake"), None) or nt.nodes.new("ShaderNodeTexImage")
        node.name = "_bake"
        node.image = img
        nt.nodes.active = node
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in selected:
        o.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    s = bpy.context.scene.render.bake
    s.use_selected_to_active = bool(selected)
    s.cage_extrusion = extrusion
    s.max_ray_distance = max_ray
    s.margin = 4
    s.use_clear = True
    if kind == "NORMAL":
        bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", uv_layer=UV)
    else:
        bpy.ops.object.bake(type="EMIT", uv_layer=UV)

def face_ids(obj, size):
    """Atlas image of which face covers each pixel (-1 for none), rasterised from the UVs."""
    me = obj.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[UV].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2) * size - 0.5
    ids = np.full((size, size), -1, dtype=np.int64)
    for t in me.loop_triangles:
        a, b, c = uv[t.loops[0]], uv[t.loops[1]], uv[t.loops[2]]
        x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (1 - l1 - l2 >= -1e-6)
        ids[Y[m], X[m]] = t.polygon_index
    return ids

def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)

def jpeg(sc, quality):
    """save_render writes in the scene's output format, not the image's: set it to JPEG."""
    s = sc.render.image_settings
    s.file_format = "JPEG"
    s.color_mode = "RGB"
    s.quality = quality
