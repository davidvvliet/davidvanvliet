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
#   distance    between two points, "from" and "to" (no "object"); each is
#               {"object": name, "at": "centre" | "bottom" | "top" | "origin"} or a spec
#               `points` name; "axis": "x" | "y" | "z" measures along one axis only
#               (wheelbase, track width, deck height)
#
# Also: `ground` (parts that stand on z = ground: contacts touch it, nothing goes through,
# nothing else touches) and `joints` (posed angles inside their sourced limits).
import fnmatch, json, os, struct
import bpy
from mathutils import Vector
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

def _point(ref, by_name, spec):
    """World point for a distance end: a spec `points` name, or {"object", "at"}."""
    if isinstance(ref, str):
        ref = spec.get("points", {})[ref]
    o = by_name[ref["object"]]
    at = ref.get("at", "centre")
    if at == "origin":
        return o.matrix_world.translation.copy()
    pts = _points([o])
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2
    if at == "bottom":
        c.z = lo.z
    elif at == "top":
        c.z = hi.z
    elif at != "centre":
        raise ValueError(f"unknown point 'at': {at}")
    return c

def distance(dim, by_name, spec):
    a, b = _point(dim["from"], by_name, spec), _point(dim["to"], by_name, spec)
    if "axis" in dim:
        i = "xyz".index(dim["axis"])
        return abs(a[i] - b[i])
    return (a - b).length

GROUND_TOUCH = 0.005  # m

def ground(spec, objs):
    """Problems with standing on the ground: [] when fine."""
    g = spec["ground"]
    z0, tol = g.get("z", 0.0), g.get("tolerance", GROUND_TOUCH)
    contacts = [o for o in objs if any(fnmatch.fnmatch(o.name, pat) for pat in g["contacts"])]
    problems = []
    if not contacts:
        problems.append("no part matches ground.contacts")
    for o in objs:
        low = min(p.z for p in _points([o]))
        if o in contacts and abs(low - z0) > tol:
            problems.append(f"{o.name} {'above' if low > z0 else 'below'} ground by {abs(low - z0) * 1000:.0f} mm")
        elif o not in contacts and low < z0 + tol:
            problems.append(f"{o.name} {'touches' if low >= z0 - tol else 'goes through'} the ground")
    return problems

def joints(spec, all_objs):
    """Posed joints outside their limits, or missing: [] when fine."""
    by_name = {o.name: o for o in all_objs}
    problems = []
    for name, j in spec.get("joints", {}).items():
        o = by_name.get(name)
        if o is None or "joint_axis" not in o:
            problems.append(f"no joint {name}")
            continue
        a = o.get("angle_deg", 0.0)
        lo, hi = j.get("min", -360), j.get("max", 360)
        if not lo - 1e-6 <= a <= hi + 1e-6:
            problems.append(f"{name} at {a:.1f}° outside {lo}..{hi}°")
    return problems

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
    """Returns a list of check results: {name, ok, measured, expected, unit, detail}.
    `objs` may include joints (empties); geometry checks use the meshes."""
    all_objs = objs
    objs = [o for o in objs if o.type == "MESH"]
    by_name = {o.name: o for o in all_objs}
    results = []
    for name, dim in spec.get("dimensions", {}).items():
        target = dim.get("object", "*")
        names = target if isinstance(target, list) else [target]
        sel = objs if names == ["*"] else [by_name[n] for n in names if n in by_name]
        res = {"name": name, "expected": dim["value"], "unit": dim.get("unit", "m"),
               "source": dim.get("source")}
        if dim.get("measure") == "distance":
            ends = [dim["from"], dim["to"]]
            names = [(spec.get("points", {}).get(e, {}) if isinstance(e, str) else e).get("object", "?") for e in ends]
        missing = [n for n in names if n != "*" and n not in by_name]
        if missing:
            res.update(ok=False, measured=None, detail=f"missing object {', '.join(missing)}")
        else:
            got = (distance(dim, by_name, spec) if dim.get("measure") == "distance"
                   else measure(sel, dim.get("measure", "length")))
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
    if "ground" in spec:
        g = ground(spec, objs)
        results.append({"name": "ground", "ok": not g, "measured": "ok" if not g else "off", "unit": "",
                        "expected": "contacts on the ground", "detail": "; ".join(g) or
                        f"{', '.join(spec['ground']['contacts'])} on z = {spec['ground'].get('z', 0)}, nothing else down there"})
    if "joints" in spec:
        j = joints(spec, all_objs)
        results.append({"name": "joints", "ok": not j, "measured": len(spec["joints"]) - len(j), "unit": "joints",
                        "expected": len(spec["joints"]), "detail": "; ".join(j) or "every posed joint inside its limits"})
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
