# Bakes a reference model's colours onto a probe (`run.py bake <probe> <model>` starts Blender
# with this file). Builds the probe, unwraps its parts into one atlas (lib/bake.py), poses the
# reference at the spec's `bake.frame`, and projects the reference's base colour onto our
# surfaces (Cycles, selected-to-active). Where a ray finds nothing within `bake.max_ray_m`
# (our shape differs from the reference), the part keeps its own sourced colour.
# Output: refs/<probe>/baked.jpg and baked.json (geometry fingerprint, coverage, settings);
# every later build applies it.
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy
import numpy as np
import build as harness
from lib import bake, materials, parts

def _world_copy(objs, name):
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

def _albedo(mats, on):
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

def _reference(path, frame, ignore):
    """The reference model posed at `frame`, as plain world-space meshes, without the
    objects in `ignore`."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    imported = [o for o in bpy.data.objects if o not in before]
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = []
    for o in imported:
        if o.type != "MESH" or o.name in ignore:
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        me.transform(o.matrix_world)
        c = bpy.data.objects.new("ref_" + o.name, me)
        bpy.context.scene.collection.objects.link(c)
        meshes.append(c)
    for o in imported:
        bpy.data.objects.remove(o)
    return meshes

def _bake_into(target, img, selected=(), extrusion=0.0, max_ray=0.0, kind="DIFFUSE"):
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
        bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", uv_layer=bake.UV)
    else:
        bpy.ops.object.bake(type="EMIT", uv_layer=bake.UV)

def _face_ids(obj, size):
    """Atlas image of which face covers each pixel (-1 for none), rasterised from the UVs."""
    me = obj.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[bake.UV].data.foreach_get("uv", uv)
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

def _pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)

def main(probe, ref_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spec = json.load(open(os.path.join(HERE, "specs", f"{probe}.json")))
    cfg = spec.get("bake") or {}
    size, frame = cfg.get("size", 2048), cfg.get("frame", 1)
    extrusion, max_ray = cfg.get("extrusion_m", 0.03), cfg.get("max_ray_m", 0.08)

    materials.use(spec.get("materials"))
    parts.clear()
    harness._load_probe(probe).build(spec)
    objs = parts.meshes(list(parts.collection().objects))
    targets = bake.unwrap(objs)
    fp = bake.fingerprint(objs)
    lay = bake.layout(objs)
    parts.pose({o.name: 0.0 for o in bake._joints()})  # the reference model's own pose
    ours = _world_copy(targets, "_target")
    ref = _reference(ref_path, frame, set(cfg.get("ignore", [])))

    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 4
    # Passes, nearest first: a face takes the first pass that reaches the reference over at
    # least min_face_hit of it. Later passes reach further for faces of stand-in shapes that
    # sit well off the reference's surface (a longer reach can pick up a part in front).
    passes = cfg.get("passes") or [{"extrusion_m": extrusion, "max_ray_m": max_ray}]
    min_hit = cfg.get("min_face_hit", 0.5)

    # Base colours, not lit colours (see _albedo); switched back for the normal bake.
    mats = {m for o in [ours] + ref for m in o.data.materials if m}
    _albedo(mats, True)
    flat = bpy.data.images.new("_flat", size, size, alpha=True)   # our own colours: the fallback
    _bake_into(ours, flat)
    F = _pixels(flat)
    face = _face_ids(ours, size)
    inside = face >= 0
    nfaces = int(face.max()) + 1
    f = np.where(inside, face, 0)
    choice = np.full(nfaces, -1)
    projs, out = [], F.copy()
    dbg_dir = os.path.join(HERE, "out", probe)
    os.makedirs(dbg_dir, exist_ok=True)
    for k, ps in enumerate(passes):
        img = bpy.data.images.new(f"_proj{k}", size, size, alpha=True)
        img.generated_color = (0, 0, 0, 0)
        _bake_into(ours, img, ref, ps["extrusion_m"], ps["max_ray_m"])
        P = _pixels(img)
        hit = P[..., 3] > 0.5
        cnt = np.bincount(face[inside], minlength=nfaces)
        hits = np.bincount(face[inside & hit], minlength=nfaces)
        frac = hits / np.maximum(cnt, 1)
        sums = np.zeros((nfaces, 4))
        np.add.at(sums, face[inside & hit], P[inside & hit])
        mean = sums / np.maximum(hits, 1)[:, None]
        new = (choice < 0) & (frac >= min_hit)
        choice[new] = k
        sel = inside & (choice[f] == k)
        out = np.where((sel & hit)[..., None], P, out)
        out = np.where((sel & ~hit)[..., None], mean[f], out)
        if k == 0:  # margins outside every face: the nearest pass, else the fallback
            out = np.where((~inside & hit)[..., None], P, out)
        img.filepath_raw = os.path.join(dbg_dir, "bake_projection.png" if k == 0 else f"bake_projection_{k}.png")
        img.file_format = "PNG"
        img.save()
    out[..., 3] = 1.0
    res = bpy.data.images.new("baked", size, size, alpha=False)
    res.pixels.foreach_set(out.astype(np.float32).ravel())
    jpg, info_path = bake.paths(HERE, probe)
    res.filepath_raw = jpg
    res.file_format = "JPEG"
    sc.render.image_settings.quality = cfg.get("jpeg_quality", 88)
    res.save_render(jpg, scene=sc)
    flat.filepath_raw = os.path.join(dbg_dir, "bake_flat.png")
    flat.file_format = "PNG"
    flat.save()

    # Normal map: the reference's surface detail (its geometry and its own normal maps) on the
    # faces that took its colour, from the same pass; flat elsewhere.
    nsize = cfg.get("normal_size", 0)
    _albedo(mats, False)
    if nsize:
        nface = face if nsize == size else _face_ids(ours, nsize)
        ninside = nface >= 0
        nf = np.where(ninside, nface, 0)
        nout = np.empty((nsize, nsize, 4), dtype=np.float32)
        nout[:] = (0.5, 0.5, 1.0, 1.0)
        for k, ps in enumerate(passes):
            if not (choice == k).any():
                continue
            img = bpy.data.images.new(f"_nproj{k}", nsize, nsize, alpha=True)
            img.colorspace_settings.name = "Non-Color"
            img.generated_color = (0, 0, 0, 0)
            _bake_into(ours, img, ref, ps["extrusion_m"], ps["max_ray_m"], kind="NORMAL")
            N = _pixels(img)
            sel = ninside & (choice[nf] == k) & (N[..., 3] > 0.5)
            nout = np.where(sel[..., None], N, nout)
        nout[..., 3] = 1.0
        nres = bpy.data.images.new("baked_normal", nsize, nsize, alpha=False)
        nres.colorspace_settings.name = "Non-Color"
        nres.pixels.foreach_set(nout.astype(np.float32).ravel())
        npath = bake.normal_path(HERE, probe)
        nres.filepath_raw = npath
        nres.file_format = "JPEG"
        sc.render.image_settings.quality = cfg.get("normal_jpeg_quality", 92)
        nres.save_render(npath, scene=sc)

    px = np.bincount(face[inside], minlength=nfaces)
    by_pass = {str(k): round(float(px[choice == k].sum() / max(px.sum(), 1)), 3) for k in range(len(passes))}
    info = {"fingerprint": fp, "layout": lay, "reference": os.path.basename(ref_path), "frame": frame, "size": size,
            "passes": passes, "parts": len(targets), "min_face_hit": min_hit,
            "coverage": round(float(px[choice >= 0].sum() / max(px.sum(), 1)), 3), "coverage_by_pass": by_pass,
            "atlas_used": round(float(inside.mean()), 3), "faces": bake.STATS.get("faces"),
            "hidden_faces": bake.STATS.get("hidden"), "normal_size": nsize}
    with open(info_path, "w") as fh:
        json.dump(info, fh, indent=1)
    print("BAKE_OK " + json.dumps(info))

if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    main(a[0], a[1])
