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
import json, os, struct
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

MOUNT_GAP = 0.003     # m: a mounted part's back face must lie within this of its host's surface
MOUNT_INSIDE = 0.002  # m: and no vertex of the part may sink deeper than this into the host

def _world(o):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    mesh = ev.to_mesh()
    mw = ev.matrix_world.copy()
    verts = [mw @ v.co for v in mesh.vertices]
    local = [v.co.copy() for v in mesh.vertices]
    mesh.calc_loop_triangles()
    tris = [t.vertices[:] for t in mesh.loop_triangles]
    ev.to_mesh_clear()
    return verts, local, tris

def mounted(part, host):
    """Problems with `part` sitting flush on `host`: its back face (lowest local z, the side
    parts are built from) must lie on the host's surface everywhere, so a disc hanging over
    an edge or corner fails, and no vertex may be buried inside the host. [] when it's fine."""
    pv, pl, _ = _world(part)
    hv, _, ht = _world(host)
    tree = BVHTree.FromPolygons(hv, ht)
    zmin = min(v.z for v in pl)
    back = [w for w, l in zip(pv, pl) if l.z - zmin < 1e-4]
    def signed(v):
        hit, normal, _, dist = tree.find_nearest(v)
        return dist if (v - hit).dot(normal) >= 0 else -dist
    off = [signed(v) for v in back]
    deep = min(signed(v) for v in pv)
    problems = []
    if deep < -MOUNT_INSIDE:
        problems.append(f"{part.name} is {-deep * 1000:.0f} mm inside {host.name}")
    far = max(abs(x) for x in off)
    if far > MOUNT_GAP:
        lifted = sum(1 for x in off if abs(x) > MOUNT_GAP)
        problems.append(f"{lifted}/{len(off)} back-face points off {host.name}'s surface (up to {far * 1000:.0f} mm)")
    return problems

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
    for name, m in spec.get("mounts", {}).items():
        res = {"name": f"mounted {name}", "unit": "", "expected": f"flush on {m['on']}"}
        if name not in by_name or m["on"] not in by_name:
            res.update(ok=False, measured=None, detail=f"missing object {name if name not in by_name else m['on']}")
        else:
            problems = mounted(by_name[name], by_name[m["on"]])
            res.update(ok=not problems, measured="flush" if not problems else "not flush",
                       detail="; ".join(problems) or f"back face on {m['on']}, nothing buried")
        results.append(res)
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

def _glb_json(path):
    with open(path, "rb") as f:
        f.read(12)
        length, kind = struct.unpack("<II", f.read(8))
        return json.loads(f.read(length)) if kind == 0x4E4F534A else {}

def textures(objs, glb):
    """Problems with image-textured parts: every image must have pixels, every part using one
    must have UVs inside [0, 1] (the images don't repeat), and the export must carry each
    image. [] when fine; None when no part is textured (the check is then left out)."""
    images, problems = set(), []
    for o in objs:
        mats = [m for m in o.data.materials if m and m.node_tree]
        tex = [n.image for m in mats for n in m.node_tree.nodes if n.type == "TEX_IMAGE"]
        if not tex:
            continue
        for img in tex:
            if img is None or img.size[0] == 0:
                problems.append(f"{o.name}: image {'missing' if img is None else img.name + ' has no pixels'}")
            else:
                images.add(img.name)
        uv = o.data.uv_layers.active
        if uv is None:
            problems.append(f"{o.name}: textured but has no UVs")
            continue
        co = [c for d in uv.data for c in d.uv]
        if co and (min(co) < -1e-4 or max(co) > 1 + 1e-4):
            problems.append(f"{o.name}: UVs outside the image ({min(co):.2f}..{max(co):.2f})")
    if not images and not problems:
        return None
    exported = len(_glb_json(glb).get("images", []))
    if exported < len(images):
        problems.append(f"export carries {exported} of {len(images)} images")
    return problems
