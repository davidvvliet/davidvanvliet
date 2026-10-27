# Breaks a reference model into the parts of our build, headless. Reference files often
# carry no part names (NASA's Voyager is three meshes, one per texture), so our own build,
# in the same frame, is the labeller: each loose piece of the reference goes to the nearest
# of our parts if it lies on or inside it (median distance of its points <= MATCH). Pieces
# no part claims are what we haven't built (or built in the wrong place); touching ones are
# grouped. `run.py explode <probe> <model>` starts Blender with this file.
# Output in out/<probe>/ref/: explode.json (per part family: reference box vs ours, and the
# unclaimed groups) and explode.png (an overview coloured by part, an exploded overview,
# then one tile per part family with our part as a cyan wireframe over the reference
# pieces, then one tile per unclaimed group).
import colorsys, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bmesh, bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import ref
from lib import rig

MATCH = 0.05         # m: a piece belongs to a part when its points are this close (median)
TOUCH = 0.01         # m: unclaimed pieces closer than this form one group
MIN_GROUP = 0.08     # m: unclaimed groups smaller than this (box diagonal) are listed, not drawn
SAMPLE = 64          # points per piece used for matching
TILE_PX, COLS = 512, 4
CORE_RADIUS = 3.0    # m: groups centred within this of the bus are in the overviews

def family(name):
    """Part family for grouping tiles: rtg_1, rtg_1_fins -> rtg; feed_leg_3 -> feed_leg."""
    return re.sub(r"_\d+$", "", re.sub(r"_fins$", "", name))

def group_of(obj):
    """A part's group: its declared assembly (parts.assembly), else its name family."""
    return obj.get("assembly") or family(obj.name)

def _world_mesh(o):
    mw = o.matrix_world
    verts = [mw @ v.co for v in o.data.vertices]
    o.data.calc_loop_triangles()
    return verts, [t.vertices[:] for t in o.data.loop_triangles]

def _box(points):
    p = np.asarray(points)
    return p.min(0), p.max(0)

def _load_build(probe):
    path = os.path.join(HERE, "out", probe, f"{probe}.blend")
    if not os.path.exists(path):
        raise SystemExit(f"no build at {path}: run `run.py build {probe}` first")
    with bpy.data.libraries.load(path) as (src, dst):
        dst.collections = [c for c in src.collections if c == "Probe"]
    col = dst.collections[0]
    bpy.context.scene.collection.children.link(col)
    bpy.context.view_layer.update()  # world matrices are only valid after an update
    return [o for o in col.all_objects if o.type == "MESH"]

def _pieces(meshes):
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and len(o.data.vertices)
            and o.users_collection[0].name != "Probe"]

def _signed_median(points, tree):
    d = []
    for v in points:
        hit, normal, _, dist = tree.find_nearest(v)
        d.append(0.0 if hit is None or (v - hit).dot(normal) < 0 else dist)
    return float(np.median(d))

def _hull_tree(verts):
    """BVH of the convex hull: a truss, finned body or dish then counts as solid, so the
    reference's bars between our bars still belong to the part."""
    bm = bmesh.new()
    for v in verts:
        bm.verts.new(v)
    try:
        bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
        tree = BVHTree.FromBMesh(bm)
    finally:
        bm.free()
    return tree

def assign(pieces, ours):
    trees, boxes = {}, {}
    for o in ours:
        verts, tris = _world_mesh(o)
        trees[o.name] = _hull_tree(verts)
        boxes[o.name] = _box(verts)
    owner, info = {}, {}
    rng = np.random.default_rng(0)
    for pc in pieces:
        pts = [Vector(p) for p in ref._points(pc)]
        lo, hi = _box(pts)
        info[pc.name] = (lo, hi, pts)
        sample = pts if len(pts) <= SAMPLE else [pts[i] for i in rng.choice(len(pts), SAMPLE, replace=False)]
        best, best_d = None, math.inf
        for name, (blo, bhi) in boxes.items():
            if np.any(lo > bhi + MATCH) or np.any(blo > hi + MATCH):
                continue
            d = _signed_median(sample, trees[name])
            if d < best_d:
                best, best_d = name, d
        owner[pc.name] = best if best_d <= MATCH else None
    return owner, info, trees, boxes

def group_unclaimed(names, info):
    """Union touching unclaimed pieces (box gap, then nearest-point distance <= TOUCH)."""
    trees = {}
    for n in names:
        o = bpy.data.objects[n]
        verts, tris = _world_mesh(o)
        trees[n] = BVHTree.FromPolygons(verts, tris)
    parent = {n: n for n in names}
    def root(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n
    for i, a in enumerate(names):
        alo, ahi, apts = info[a]
        for b in names[i + 1:]:
            blo, bhi, bpts = info[b]
            if np.any(alo > bhi + TOUCH) or np.any(blo > ahi + TOUCH) or root(a) == root(b):
                continue
            small, tree = (apts, trees[b]) if len(apts) < len(bpts) else (bpts, trees[a])
            if trees[a].overlap(trees[b]) or any(
                    (h := tree.find_nearest(v))[0] is not None and h[3] <= TOUCH for v in small[::max(1, len(small) // 64)]):
                parent[root(a)] = root(b)
    groups = {}
    for n in names:
        groups.setdefault(root(n), []).append(n)
    return list(groups.values())

def _colour(i):
    hue = 0.13 + ((i * 0.618034) % 1) * 0.72  # never red: red marks unclaimed pieces
    r, g, b = colorsys.hsv_to_rgb(hue, 0.5, 0.95)
    return (r, g, b, 1)

def _flat(name, rgba, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = rgba
    if emit:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emit
    return m

def _label(cam, text, dist):
    """White text in the top-left corner of `cam`'s view."""
    curve = bpy.data.curves.new(f"Label_{cam.name}", "FONT")
    curve.body = text
    obj = bpy.data.objects.new(curve.name, curve)
    rig._collection().objects.link(obj)
    obj.parent = cam
    d = dist * 0.3
    half = d * math.tan(math.atan(cam.data.sensor_width / (2 * cam.data.lens)))
    curve.size = half * 0.075
    obj.location = (-half * 0.94, half * 0.86, -d)
    obj.data.materials.append(_flat("label", (1, 1, 1, 1), emit=1.0))
    return obj

def render_tiles(tiles, out_dir):
    """tiles: [{"name", "label", "show": [objs], "target", "radius", "look"}] -> explode.png"""
    scene = bpy.context.scene
    for o in [o for o in rig._collection().objects if o.type == "FONT"]:
        curve = o.data
        bpy.data.objects.remove(o)
        bpy.data.curves.remove(curve)
    rig.clear()
    rig._setup_scene()
    scene.render.resolution_x = scene.render.resolution_y = TILE_PX
    scene.render.film_transparent = False
    lights = [o for o in rig._collection().objects if o.type == "LIGHT"]
    every = [o for o in scene.objects if o.type in ("MESH", "FONT")]
    tdir = os.path.join(out_dir, "explode")
    os.makedirs(tdir, exist_ok=True)
    paths = []
    for i, t in enumerate(tiles):
        look = Vector(t.get("look", (-1, 1, -0.6))).normalized()
        cam = bpy.data.cameras.new(f"Explode_{i}")
        obj = bpy.data.objects.new(f"Explode_{i}", cam)
        rig._collection().objects.link(obj)
        obj.matrix_world = rig._aim(look, Vector((0, 0, 1)) if abs(look.z) < 0.95 else Vector((0, 1, 0)))
        cam.lens = 50
        fov = 2 * math.atan(cam.sensor_width / (2 * cam.lens))
        dist = max(t["radius"], 0.05) * 1.15 / math.sin(fov / 2)
        obj.location = Vector(t["target"]) - look * dist
        cam.clip_start, cam.clip_end = dist * 0.01, dist * 50
        label = _label(obj, t["label"], dist)
        show = set(t["show"]) | {label} | set(lights)
        for o in every + [label]:
            o.hide_render = o not in show
        bpy.context.view_layer.update()
        scene.camera = obj
        path = os.path.join(tdir, f"{i:02d}_{t['name']}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        label.hide_render = True
        every.append(label)
        paths.append(path)
    imgs = [rig._load(p) for p in paths]
    blank = np.empty_like(imgs[0])
    blank[:] = imgs[0][0, 0]
    while len(imgs) % COLS:
        imgs.append(blank)
    rows = [np.concatenate(imgs[i:i + COLS], axis=1) for i in range(0, len(imgs), COLS)]
    rig.save_png(np.concatenate(rows[::-1], axis=0), os.path.join(out_dir, "explode.png"))

def _r(v):
    return [round(float(x), 3) for x in v]

def main(probe, path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ref._import(path)
    pieces = _pieces(ref._bake())
    ours = _load_build(probe)
    owner, info, trees, our_boxes = assign(pieces, ours)

    fams = {}
    for o in ours:
        fams.setdefault(group_of(o), []).append(o.name)
    claimed = {}
    for pc, part in owner.items():
        if part:
            claimed.setdefault(group_of(bpy.data.objects[part]), []).append(pc)
    unclaimed = [pc for pc, part in owner.items() if part is None]
    groups = group_unclaimed(unclaimed, info)

    def ref_box(names):
        return (np.min([info[n][0] for n in names], 0), np.max([info[n][1] for n in names], 0))
    try:  # which build this breakdown is of, so the dashboard can tell when it is stale
        started = json.load(open(os.path.join(HERE, "out", "status.json")))["probes"][probe]["started"]
    except (OSError, KeyError, ValueError):
        started = None
    report = {"model": os.path.basename(path), "build_started": started, "pieces": len(pieces),
              "claimed": len(pieces) - len(unclaimed), "match_m": MATCH, "families": {}, "unclaimed": []}
    for fam, names in fams.items():
        olo = np.min([our_boxes[n][0] for n in names], 0)
        ohi = np.max([our_boxes[n][1] for n in names], 0)
        row = {"parts": names, "ours": {"min": _r(olo), "max": _r(ohi), "size": _r(ohi - olo)}}
        if fam in claimed:
            rlo, rhi = ref_box(claimed[fam])
            row["ref"] = {"pieces": len(claimed[fam]), "min": _r(rlo), "max": _r(rhi), "size": _r(rhi - rlo)}
            row["centre_offset"] = _r((rlo + rhi) / 2 - (olo + ohi) / 2)
        else:
            row["ref"] = None
        report["families"][fam] = row
    # Centre the overviews push away from: the core assembly (parts.assembly(core=True)), else "bus".
    core = [o.name for o in ours if o.get("core")] or [n for n in ("bus",) if n in our_boxes]
    bus = np.array([0.0, 0.0, 0.0])
    if core:
        bus = (np.min([our_boxes[n][0] for n in core], 0) + np.max([our_boxes[n][1] for n in core], 0)) / 2
    for g in sorted(groups, key=lambda g: -np.linalg.norm(np.subtract(*ref_box(g)[::-1]))):
        lo, hi = ref_box(g)
        c = (lo + hi) / 2
        pts = [p for n in g for p in info[n][2]]
        pts = pts[::max(1, len(pts) // 256)]
        dists = {n: _signed_median(pts, trees[n]) for n in our_boxes}
        near = min(dists, key=dists.get)
        report["unclaimed"].append({"pieces": len(g), "names": g, "min": _r(lo), "max": _r(hi), "size": _r(hi - lo),
                                    "centre": _r(c), "nearest_part": near, "nearest_m": round(dists[near], 3),
                                    "drawn": bool(np.linalg.norm(hi - lo) >= MIN_GROUP)})

    # Materials: each family a colour in the overview; unclaimed red; ours a cyan wireframe.
    by_name = {o.name: o for o in pieces}
    originals = {o.name: list(o.data.materials) for o in pieces}
    fam_list = list(fams)
    fam_mat = {f: _flat(f"fam_{f}", _colour(i)) for i, f in enumerate(fam_list)}
    red = _flat("unclaimed", (1.0, 0.12, 0.1, 1), emit=0.6)
    wire_mat = _flat("ours", (0.1, 0.9, 1.0, 1), emit=2.0)
    def paint(objs, mat):
        for o in objs:
            o.data.materials.clear(); o.data.materials.append(mat)
    def restore(objs):
        for o in objs:
            o.data.materials.clear()
            for m in originals[o.name]:
                o.data.materials.append(m)

    def frame_of(objs_or_boxes):
        lo = np.min([b[0] for b in objs_or_boxes], 0); hi = np.max([b[1] for b in objs_or_boxes], 0)
        return list((lo + hi) / 2), float(np.linalg.norm(hi - lo) / 2)

    core_pieces = [p for p in pieces if np.linalg.norm((info[p.name][0] + info[p.name][1]) / 2 - bus) < CORE_RADIUS]
    target, radius = frame_of([info[p.name][:2] for p in core_pieces])
    for o in ours:
        o.hide_render = True
    tiles_overview = [{"name": "overview", "label": "reference coloured by our part (red: unclaimed)",
                       "show": core_pieces, "target": target, "radius": radius * 0.45}]
    # Exploded copies: each family's pieces pushed out from the bus centre.
    exploded = []
    for fam, pcs in list(claimed.items()) + [(f"unclaimed_{i}", g) for i, g in enumerate(groups)]:
        lo, hi = ref_box(pcs)
        c = (lo + hi) / 2
        if np.linalg.norm(c - bus) > CORE_RADIUS:
            continue
        off = (c - bus) * 1.2  # pushed out to 2.2x its distance from the bus
        for n in pcs:
            cp = by_name[n].copy()
            bpy.context.scene.collection.objects.link(cp)
            cp.location = Vector(off)  # shares the mesh, so it gets the family colour too
            exploded.append(cp)
    tiles_overview.append({"name": "exploded", "label": "exploded: each part pushed out from the bus",
                           "show": exploded, "target": target, "radius": radius * 0.9})
    for f in fam_list:
        paint([by_name[n] for n in claimed.get(f, [])], fam_mat[f])
    paint([by_name[n] for n in unclaimed], red)
    render_tiles(tiles_overview, os.path.join(HERE, "out", probe, "ref", "_overview"))
    for o in exploded:
        bpy.data.objects.remove(o)
    restore(pieces)

    # Per family: reference pieces (own textures) + our part as a wireframe.
    tiles = []
    wires = []
    for f in fam_list:
        names = fams[f]
        wire = []
        for n in names:
            src = bpy.data.objects[n]
            w = src.copy()
            bpy.context.scene.collection.objects.link(w)
            w.data = src.data.copy()
            w.data.materials.clear(); w.data.materials.append(wire_mat)
            boxes = [our_boxes[n] for n in names] + [info[p][:2] for p in claimed.get(f, [])]
            span = float(np.linalg.norm(np.max([b[1] for b in boxes], 0) - np.min([b[0] for b in boxes], 0)))
            mod = w.modifiers.new("wire", "WIREFRAME")
            mod.thickness = max(span * 0.004, 0.002)
            wire.append(w)
        wires += wire
        boxes = [our_boxes[n] for n in names] + [info[p][:2] for p in claimed.get(f, [])]
        t, r = frame_of(boxes)
        row = report["families"][f]
        if row["ref"]:
            o = row["centre_offset"]
            lab = f"{f}: {row['ref']['pieces']} ref pieces, centre off {math.hypot(*o) * 100:.0f} cm"
        else:
            lab = f"{f}: no reference pieces"
        tiles.append({"name": f, "label": lab, "show": [by_name[p] for p in claimed.get(f, [])] + wire,
                      "target": t, "radius": r})
    for i, u in enumerate(report["unclaimed"]):
        if not u["drawn"]:
            continue
        t, r = frame_of([(np.array(u["min"]), np.array(u["max"]))])
        tiles.append({"name": f"unclaimed_{i}", "label": f"unclaimed {i}: {u['pieces']} pieces, "
                      f"{max(u['size']) * 100:.0f} cm, {u['nearest_m'] * 100:.0f} cm from {u['nearest_part']}",
                      "show": [by_name[n] for n in u["names"]], "target": t, "radius": max(r, 0.1)})
    out = os.path.join(HERE, "out", probe, "ref")
    render_tiles(tiles, out)
    # Overview tiles go first in the combined image.
    over = rig._load(os.path.join(out, "_overview", "explode.png"))
    main_img = rig._load(os.path.join(out, "explode.png"))
    pad = np.empty((over.shape[0], main_img.shape[1] - over.shape[1], 4), dtype=np.float32)
    pad[:] = over[0, 0]
    rig.save_png(np.concatenate([main_img, np.concatenate([over, pad], axis=1)], axis=0),
                 os.path.join(out, "explode.png"))
    for u in report["unclaimed"]:
        u.pop("names")
    with open(os.path.join(out, "explode.json"), "w") as f:
        json.dump(report, f, indent=1)
    print("EXPLODE_OK " + json.dumps({"pieces": report["pieces"], "claimed": report["claimed"],
                                      "unclaimed_groups": len(report["unclaimed"]),
                                      "drawn": sum(u["drawn"] for u in report["unclaimed"])}))

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    main(args[0], args[1])
