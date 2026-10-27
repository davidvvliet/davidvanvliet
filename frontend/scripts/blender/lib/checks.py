# Checks a built probe against its spec. Measurements are taken from the evaluated
# geometry, not from the numbers the probe script was given, so a wrong formula shows.
#
# A spec dimension:
#   "dish_diameter": {"value": 3.66, "object": "dish", "measure": "diameter",
#                     "tolerance": 0.03, "source": "https://..."}
# `object` is a name, a list of names, or "*" for the whole probe. `measure`:
#   x, y, z     world-space extent
#   length      extent along the (first) object's local Z axis
#   diameter    twice the largest distance from that axis
import os
import bpy
from mathutils.bvhtree import BVHTree

DEFAULT_TOLERANCE = 0.03  # relative

def _points(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in objs:
        ev = obj.evaluated_get(dg)
        mesh = ev.to_mesh()
        mw = ev.matrix_world
        pts.extend(mw @ v.co for v in mesh.vertices)
        ev.to_mesh_clear()
    return pts

def measure(objs, kind):
    pts = _points(objs)
    if not pts:
        return None
    if kind in ("x", "y", "z"):
        i = "xyz".index(kind)
        vals = [p[i] for p in pts]
        return max(vals) - min(vals)
    mw = objs[0].matrix_world
    origin, axis = mw.translation, mw.col[2].xyz.normalized()
    if kind == "length":
        vals = [(p - origin).dot(axis) for p in pts]
        return max(vals) - min(vals)
    if kind == "diameter":
        return 2 * max(((p - origin) - axis * (p - origin).dot(axis)).length for p in pts)
    raise ValueError(f"unknown measure '{kind}'")

def triangles(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for obj in objs:
        ev = obj.evaluated_get(dg)
        mesh = ev.to_mesh()
        mesh.calc_loop_triangles()
        n += len(mesh.loop_triangles)
        ev.to_mesh_clear()
    return n

ATTACH_GAP = 0.02  # m: parts closer than this count as touching

def attached(objs):
    """Names of the parts not connected (through touching parts) to the largest group."""
    dg = bpy.context.evaluated_depsgraph_get()
    trees, pts, boxes = {}, {}, {}
    for o in objs:
        ev = o.evaluated_get(dg)
        mesh = ev.to_mesh()
        mw = ev.matrix_world
        verts = [mw @ v.co for v in mesh.vertices]
        mesh.calc_loop_triangles()
        trees[o.name] = BVHTree.FromPolygons(verts, [t.vertices[:] for t in mesh.loop_triangles])
        pts[o.name] = verts
        boxes[o.name] = ([min(v[i] for v in verts) for i in range(3)], [max(v[i] for v in verts) for i in range(3)])
        ev.to_mesh_clear()
    names = list(pts)
    def near(a, b):
        (alo, ahi), (blo, bhi) = boxes[a], boxes[b]
        if any(alo[i] > bhi[i] + ATTACH_GAP or blo[i] > ahi[i] + ATTACH_GAP for i in range(3)):
            return False
        if trees[a].overlap(trees[b]):
            return True
        for x, y in ((a, b), (b, a)):
            for v in pts[x]:
                hit, normal, _, dist = trees[y].find_nearest(v)
                # touching, or inside the other part (behind its nearest face; parts are closed)
                if hit is not None and (dist <= ATTACH_GAP or (v - hit).dot(normal) < 0):
                    return True
        return False
    groups = []
    for n in names:  # union of touching parts
        joined = [g for g in groups if any(near(n, m) for m in g)]
        merged = {n}.union(*joined) if joined else {n}
        groups = [g for g in groups if g not in joined] + [merged]
    main = max(groups, key=len)
    return sorted(n for n in names if n not in main)

def run(spec, objs):
    """Returns a list of check results: {name, ok, measured, expected, unit, detail}."""
    by_name = {o.name: o for o in objs}
    results = []
    for name, dim in spec.get("dimensions", {}).items():
        target = dim.get("object", "*")
        names = target if isinstance(target, list) else [target]
        sel = objs if names == ["*"] else [by_name[n] for n in names if n in by_name]
        res = {"name": name, "expected": dim["value"], "unit": dim.get("unit", "m"),
               "source": dim.get("source")}
        missing = [n for n in names if n != "*" and n not in by_name]
        if missing:
            res.update(ok=False, measured=None, detail=f"missing object {', '.join(missing)}")
        else:
            got = measure(sel, dim.get("measure", "length"))
            tol = dim.get("tolerance", DEFAULT_TOLERANCE)
            err = (got - dim["value"]) / dim["value"] if dim["value"] else got
            res.update(ok=abs(err) <= tol, measured=round(got, 4),
                       detail=f"{err * 100:+.1f}% (tolerance ±{tol * 100:.0f}%)")
        results.append(res)
    loose = [] if "attached" in spec.get("skip_checks", []) else attached(objs)
    if "attached" not in spec.get("skip_checks", []):
        results.append({"name": "attached", "ok": not loose, "measured": len(objs) - len(loose),
                        "expected": len(objs), "unit": "parts",
                        "detail": "floating: " + ", ".join(loose) if loose else "every part touches the craft"})
    budget = spec.get("budget", {})
    tris = triangles(objs)
    max_tris = budget.get("triangles", 50000)
    results.append({"name": "triangles", "ok": tris <= max_tris, "measured": tris,
                    "expected": max_tris, "unit": "tris", "detail": "budget"})
    return results

def file_size(path, spec):
    max_bytes = spec.get("budget", {}).get("glb_bytes", 1_500_000)
    size = os.path.getsize(path)
    return {"name": "glb size", "ok": size <= max_bytes, "measured": size, "expected": max_bytes,
            "unit": "bytes", "detail": "budget"}
