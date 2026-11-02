# Cut whole loose pieces out of a reference model into a mesh file a probe script can load
# with parts.mesh_file (for hardware no document gives the shape of: copied, not redrawn).
#
#   blender -b --python tools/cut.py -- <model> <out.json> x0 y0 z0 x1 y1 z1
#           [--matrix m00,m01,m02,m03,m10,...,m23] [--min M] [--max M] [--rmin R] [--rmax R] [--decimate R] [--inside] [--material NAME] [--occluder MESH.json]
#
#   --matrix    12 comma-separated numbers (3 rows of 4): maps the imported model into the probe's frame
#               before the box test, so the box and the output are in probe coordinates
#   --min/--max keep pieces whose largest bounds size is within [M, M] metres
#   --rmin/--rmax  keep pieces whose centre is within [R, R] of the z axis (skip a body's insides)
#   --inside    keep only pieces lying wholly inside the box (not just their centre)
#   --material  keep pieces whose first face uses a material whose name starts with NAME
#   --occluder  drop pieces hidden inside this mesh file (a cut, in the probe's frame): every
#               vertex's rays in 14 directions hit it (bare hardware under a blanket)
#   --decimate  keep this share of the triangles (Blender's collapse decimation)
#
# The output is JSON: the cut's settings (for the record) plus "vertices" and "faces".
# Inputs are data: nothing in the model is run.
import json, os, sys
import bmesh, bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces import _import

def _args():
    a = sys.argv[sys.argv.index("--") + 1:]
    model, out = a[0], a[1]
    lo, hi = np.array(a[2:5], float), np.array(a[5:8], float)
    opts = {"--min": 0.0, "--max": float("inf"), "--decimate": 1.0, "--rmin": 0.0, "--rmax": float("inf")}
    m = None
    opts["--inside"] = False
    opts["--material"] = None
    opts["--occluder"] = None
    i = 8
    while i < len(a):
        if a[i] == "--occluder":
            opts["--occluder"] = a[i + 1]
            i += 2
        elif a[i] == "--material":
            opts["--material"] = a[i + 1]
            i += 2
        elif a[i] == "--inside":
            opts["--inside"] = True
            i += 1
        elif a[i] == "--matrix":
            m = [float(x) for x in a[i + 1].split(",")]
            if len(m) != 12:
                raise SystemExit("--matrix takes 12 comma-separated numbers")
            i += 2
        elif a[i] in opts:
            opts[a[i]] = float(a[i + 1])
            i += 2
        else:
            raise SystemExit(f"unknown option {a[i]}")
    return model, out, lo, hi, m, opts

DIRS = [Vector(d).normalized() for d in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        + [(x, y, z) for x in (1, -1) for y in (1, -1) for z in (1, -1)]]

def _occluder(path):
    with open(path) as f:
        r = json.load(f)
    return BVHTree.FromPolygons([tuple(v) for v in r["vertices"]], [tuple(p) for p in r["faces"]])

def _hidden(tree, pts):
    """Every point is boxed in: a ray in each direction hits the occluder."""
    return all(tree.ray_cast(Vector(p), d)[0] is not None for p in pts for d in DIRS)

def main():
    model, out, lo, hi, m, opts = _args()
    occ = _occluder(opts["--occluder"]) if opts["--occluder"] else None
    hidden = 0
    _import(model)
    M = Matrix((m[0:4], m[4:8], m[8:12], (0, 0, 0, 1))) if m else Matrix()
    keep = bmesh.new()
    dg = bpy.context.evaluated_depsgraph_get()
    pieces = 0
    for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        me.transform(o.matrix_world)
        me.transform(M)
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        seen = set()
        for v in bm.verts:
            if v.index in seen:
                continue
            stack, comp = [v], []
            seen.add(v.index)
            while stack:
                x = stack.pop(); comp.append(x)
                for e in x.link_edges:
                    y = e.other_vert(x)
                    if y.index not in seen:
                        seen.add(y.index); stack.append(y)
            P = np.array([x.co[:] for x in comp])
            c, s = (P.min(0) + P.max(0)) / 2, P.max(0) - P.min(0)
            if not (np.all((c > lo) & (c < hi)) and opts["--min"] <= s.max() <= opts["--max"]
                    and opts["--rmin"] <= np.hypot(c[0], c[1]) <= opts["--rmax"]
                    and (not opts["--inside"] or (np.all(P.min(0) >= lo) and np.all(P.max(0) <= hi)))):
                continue
            if opts["--material"] is not None:
                f0 = next(iter(comp[0].link_faces), None)
                mat = me.materials[f0.material_index] if f0 is not None and len(me.materials) else None
                if not (mat and mat.name.startswith(opts["--material"])):
                    continue
            if occ is not None and _hidden(occ, P):
                hidden += 1
                continue
            pieces += 1
            new = {x.index: keep.verts.new(x.co) for x in comp}
            faces = {f for x in comp for f in x.link_faces}
            for f in faces:
                try:
                    keep.faces.new([new[x.index] for x in f.verts])
                except ValueError:
                    pass
        bm.free()
    mesh = bpy.data.meshes.new("cut")
    keep.to_mesh(mesh); keep.free()
    if opts["--decimate"] < 1.0:
        obj = bpy.data.objects.new("cut", mesh)
        bpy.context.scene.collection.objects.link(obj)
        mod = obj.modifiers.new("dec", "DECIMATE")
        mod.ratio = opts["--decimate"]
        dg = bpy.context.evaluated_depsgraph_get()
        dec = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
        # Collapsing thin flat parts can throw a vertex metres away: drop faces that left the surface
        tree = BVHTree.FromPolygons([v.co[:] for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons])
        bm = bmesh.new(); bm.from_mesh(dec)
        far = {v for v in bm.verts if (lambda h: h[0] is None or h[3] > 0.005)(tree.find_nearest(v.co))}
        bmesh.ops.delete(bm, geom=list({f for v in far for f in v.link_faces}), context="FACES_ONLY")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(dec); bm.free()
        mesh = dec
    verts = [[round(c, 4) for c in v.co] for v in mesh.vertices]
    faces = [list(p.vertices) for p in mesh.polygons]
    rec = {"model": os.path.basename(model), "box": [lo.tolist(), hi.tolist()], "matrix": m,
           "min": opts["--min"], "max": opts["--max"] if opts["--max"] != float("inf") else None,
           "decimate": opts["--decimate"], "rmin": opts["--rmin"], "rmax": opts["--rmax"] if opts["--rmax"] != float("inf") else None, "inside": opts["--inside"], "material": opts["--material"], "occluder": opts["--occluder"] and os.path.basename(opts["--occluder"]), "hidden": hidden, "pieces": pieces, "vertices": verts, "faces": faces}
    with open(out, "w") as f:
        json.dump(rec, f, separators=(",", ":"))
    tris = sum(len(p) - 2 for p in faces)
    print(f"CUT_OK {out} pieces {pieces} hidden {hidden} vertices {len(verts)} triangles {tris}")

main()
