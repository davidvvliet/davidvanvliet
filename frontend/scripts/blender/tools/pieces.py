# Lists a reference model's loose pieces inside a box region (Blender script; run through
# `run.py pieces`). A piece is in the region when the centre of its bounds is.
#
#   blender -b --python tools/pieces.py -- <model> x0 y0 z0 x1 y1 z1 [--min M] [--max M]
#           [--struts] [--dump]
#
#   default   one line per piece: material, vertex count, bounds centre and size, and the
#             principal axis (the direction the piece is longest in), largest first
#   --struts  rods only (at least 15 cm long and 5x longer than thick). A strut in NASA's
#             models is several flat faces; these are merged and printed as one line with
#             its two end points and thickness, lower end first
#   --dump    every piece's vertices as JSON (PIECE [[x, y, z], ...]), to fit a shape to
#   --min/--max  skip pieces whose largest bounds size is below / above M metres
#
# The model is data: it is imported, never executed.
import sys
import bpy, bmesh
import numpy as np

def _args():
    a = sys.argv[sys.argv.index("--") + 1:]
    flags = {"--struts": False, "--dump": False}
    opts = {"--min": 0.0, "--max": float("inf")}
    pos, i = [], 0
    while i < len(a):
        if a[i] in flags:
            flags[a[i]] = True
        elif a[i] in opts:
            opts[a[i]] = float(a[i + 1]); i += 1
        else:
            pos.append(a[i])
        i += 1
    if len(pos) != 7:
        raise SystemExit("usage: pieces.py -- <model> x0 y0 z0 x1 y1 z1 [--min M] [--max M] [--struts] [--dump]")
    return pos[0], np.array([float(x) for x in pos[1:4]]), np.array([float(x) for x in pos[4:7]]), flags, opts

def _import(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext = path.lower().rsplit(".", 1)[-1]
    if ext in ("glb", "gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == "obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == "fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == "stl":
        bpy.ops.wm.stl_import(filepath=path)
    else:
        raise SystemExit(f"unsupported model type: {path}")

def loose_pieces(lo, hi):
    """(material name, vertex array) for each loose piece whose bounds centre is in [lo, hi]."""
    dg = bpy.context.evaluated_depsgraph_get()
    for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        me.transform(o.matrix_world)
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        vmat = {}
        for f in bm.faces:
            for v in f.verts:
                vmat[v.index] = f.material_index
        seen = set()
        for v in bm.verts:
            if v.index in seen:
                continue
            stack, comp = [v], []
            seen.add(v.index)
            while stack:
                x = stack.pop(); comp.append(x.index)
                for e in x.link_edges:
                    y = e.other_vert(x)
                    if y.index not in seen:
                        seen.add(y.index); stack.append(y)
            P = np.array([bm.verts[i].co[:] for i in comp])
            c = (P.min(0) + P.max(0)) / 2
            if not np.all((c > lo) & (c < hi)):
                continue
            mi = vmat.get(comp[0], 0)
            slot = o.material_slots[mi] if mi < len(o.material_slots) else None
            yield (slot.material.name if slot and slot.material else f"{o.name}:-"), P

def _axis(P):
    if len(P) < 3:
        return np.zeros(3)
    return np.linalg.svd(P - P.mean(0), full_matrices=False)[2][0]

def main():
    model, lo, hi, flags, opts = _args()
    _import(model)
    rows = []
    for mat, P in loose_pieces(lo, hi):
        s = P.max(0) - P.min(0)
        if not opts["--min"] <= max(s) <= opts["--max"]:
            continue
        rows.append((mat, P, s))
    if flags["--dump"]:
        for mat, P, s in rows:
            print("PIECE", np.round(P, 4).tolist())
        print("COUNT", len(rows))
        return
    if flags["--struts"]:
        rods = []
        for mat, P, s in rows:
            if len(P) < 4:
                continue
            m = P.mean(0); ax = _axis(P); t = (P - m) @ ax
            thick = np.linalg.norm((P - m) - np.outer(t, ax), axis=1).max()
            L = t.max() - t.min()
            if L >= 0.15 and L >= 5 * thick:
                rods.append((m + ax * t.min(), m + ax * t.max(), thick))
        groups = []   # faces of one strut share both end points (within 4 cm)
        for a, b, r in rods:
            for g in groups:
                if ((np.linalg.norm(a - g[0]) < .04 and np.linalg.norm(b - g[1]) < .04)
                        or (np.linalg.norm(a - g[1]) < .04 and np.linalg.norm(b - g[0]) < .04)):
                    g[2].append((a, b, r)); break
            else:
                groups.append([a, b, [(a, b, r)]])
        for g in groups:
            A = np.mean([x[0] if np.linalg.norm(x[0] - g[0]) < .04 else x[1] for x in g[2]], axis=0)
            B = np.mean([x[1] if np.linalg.norm(x[0] - g[0]) < .04 else x[0] for x in g[2]], axis=0)
            if A[2] > B[2]:
                A, B = B, A
            # thickness: one face's half-width, or the spread of the merged faces' centres
            spread = np.ptp([(x[0] + x[1]) / 2 for x in g[2]], axis=0).max() if len(g[2]) > 1 else 0.0
            r = max(max(x[2] for x in g[2]), spread / 2)
            print(f"STRUT faces {len(g[2])}  {np.round(A, 3).tolist()} -> {np.round(B, 3).tolist()}  "
                  f"length {np.linalg.norm(B - A):.3f}  radius ~{r:.3f}")
        print("COUNT", len(groups))
        return
    rows.sort(key=lambda r: -np.prod(np.maximum(r[2], 0.02)))
    for mat, P, s in rows:
        c = (P.min(0) + P.max(0)) / 2
        print(f"{mat[:16]:16s} v{len(P):5d}  centre {np.round(c, 3).tolist()}  size {np.round(s, 3).tolist()}  "
              f"axis {np.round(_axis(P), 2).tolist()}")
    print("COUNT", len(rows))

if __name__ == "__main__":
    main()
