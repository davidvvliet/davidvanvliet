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
    ours = bake.world_copy(targets, "_target")
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
    bake.albedo(mats, True)
    flat = bpy.data.images.new("_flat", size, size, alpha=True)   # our own colours: the fallback
    bake.bake_into(ours, flat)
    F = bake.pixels(flat)
    face = bake.face_ids(ours, size)
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
        bake.bake_into(ours, img, ref, ps["extrusion_m"], ps["max_ray_m"])
        P = bake.pixels(img)
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
    bake.jpeg(sc, cfg.get("jpeg_quality", 88))
    res.save_render(jpg, scene=sc)
    flat.filepath_raw = os.path.join(dbg_dir, "bake_flat.png")
    flat.file_format = "PNG"
    flat.save()

    # Normal map: the reference's surface detail (its geometry and its own normal maps) on the
    # faces that took its colour, from the same pass; flat elsewhere.
    nsize = cfg.get("normal_size", 0)
    bake.albedo(mats, False)
    if nsize:
        nface = face if nsize == size else bake.face_ids(ours, nsize)
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
            bake.bake_into(ours, img, ref, ps["extrusion_m"], ps["max_ray_m"], kind="NORMAL")
            N = bake.pixels(img)
            sel = ninside & (choice[nf] == k) & (N[..., 3] > 0.5)
            nout = np.where(sel[..., None], N, nout)
        nout[..., 3] = 1.0
        nres = bpy.data.images.new("baked_normal", nsize, nsize, alpha=False)
        nres.colorspace_settings.name = "Non-Color"
        nres.pixels.foreach_set(nout.astype(np.float32).ravel())
        npath = bake.normal_path(HERE, probe)
        nres.filepath_raw = npath
        nres.file_format = "JPEG"
        bake.jpeg(sc, cfg.get("normal_jpeg_quality", 92))
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
