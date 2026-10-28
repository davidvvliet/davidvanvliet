# Shared parts: operations on a part's skin (a hole in a cap, a plate cut out as a shell,
# decals laid on a curved surface). Imported through lib/parts.py.
import contextlib, math
import bmesh, bpy
from mathutils import Matrix, Vector

from . import materials
from .parts_core import _object

def cap_hole(obj, center, normal, radius):
    """Open a round hole of `radius` (m) in `obj`'s flat cap through `center` facing `normal`
    (a nozzle's opening in a base): the cap becomes a ring from its own outline in to the
    hole, one quad per outline edge. The outline must lie outside the hole all round."""
    c, n = Vector(center), Vector(normal).normalized()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    mw, mi = obj.matrix_world, obj.matrix_world.inverted()
    cap = [f for f in bm.faces if all(abs((mw @ v.co - c).dot(n)) < 1e-5 for v in f.verts)]
    if not cap:
        raise ValueError(f"cap_hole {obj.name}: no flat cap at {tuple(c)}")
    edges = {e for f in cap for e in f.edges if not all(g in cap for g in e.link_faces)}
    bmesh.ops.delete(bm, geom=cap, context="FACES_ONLY")
    inner = {}
    for v in {v for e in edges for v in e.verts}:
        d = mw @ v.co - c
        d -= n * d.dot(n)
        if d.length <= radius:
            raise ValueError(f"cap_hole {obj.name}: outline inside the hole at {tuple(round(x, 3) for x in mw @ v.co)}")
        inner[v] = bm.verts.new(mi @ (c + d.normalized() * radius))
    for e in edges:
        a, b = e.verts
        f = bm.faces.new((a, b, inner[b], inner[a]))
        if (mw.to_3x3() @ f.normal).dot(n) < 0:
            f.normal_flip()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj

def shell(obj, keep, thickness):
    """Keep only `obj`'s faces for which `keep(face, world_vertices)` is true and give them
    `thickness` (m) inward, against their normals: a part becomes its skin, open where the
    rest was (a speed brake's plate, with the slot behind it). Returns `obj`."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    mw = obj.matrix_world
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f, [mw @ v.co for v in f.verts])],
                     context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    if not bm.faces:
        raise ValueError(f"shell {obj.name}: no faces kept")
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=-thickness)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj

# --- Painted markings -----------------------------------------------------------------

def _host_tree(host):
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    ev = host.evaluated_get(dg)
    mesh = ev.to_mesh()
    mw = ev.matrix_world.copy()
    verts = [mw @ v.co for v in mesh.vertices]
    mesh.calc_loop_triangles()
    tree = BVHTree.FromPolygons(verts, [t.vertices[:] for t in mesh.loop_triangles])
    ev.to_mesh_clear()
    return tree

def decal(name, host, center, direction, up, width, height, material, lift=0.002, step=0.02,
          parent=None, clip=False):
    """A painted marking (lettering, an insignia) on a curved skin: a sheet laid on `host`,
    `lift` m off it, so it follows the curve and never flickers against it. `center` is a
    point at the marking's middle (on or near the skin), `direction` the way it is looked at
    (into the skin), `up` the image's top. `width` x `height` is measured along the skin: the
    sheet wraps by arc length, so lettering keeps its size where the skin curves away. Its
    UVs cover the image's [0, 1]^2; give it a cut-out material (`materials.image(...,
    cutout=True)` with a `textures.marking` image). Every vertex is in the vertex group "back",
    which the `mounted` check reads as the face on the host. Raises if any of it misses, unless
    `clip`: then the part hanging past the skin's edge (a leading edge) is left out; its image
    there should be clear."""
    d = Vector(direction).normalized()
    v0 = Vector(up) - d * Vector(up).dot(d)
    if v0.length < 1e-6:
        raise ValueError(f"decal {name}: `up` is along `direction`")
    v0.normalize()
    u0 = d.cross(v0)  # the image's right, seen from the front
    c0 = Vector(center)
    tree = _host_tree(host)
    reach = 2 * max(width, height) + 1.0

    def cast(p):
        hit, normal, _, _ = tree.ray_cast(p - d * reach, d, 2 * reach)
        if hit is None:
            if clip:
                return None, None
            raise ValueError(f"decal {name}: misses {host.name} near {tuple(round(x, 3) for x in p)}")
        return hit, (normal if normal.dot(d) < 0 else -normal)

    def wrap(line, length, n):
        """Plane offsets along `line(t)` whose arc lengths on the skin, from t = 0, are evenly
        spaced over `length` (n + 1 of them). The skin is never shorter than the plane, so
        sampling t over +-length/2 always reaches the ends."""
        k = 64
        ts = [length * (i / k - 0.5) for i in range(k + 1)]
        pts = [cast(line(t))[0] or line(t) for t in ts]
        arc = [0.0]
        for a, b in zip(pts, pts[1:]):
            arc.append(arc[-1] + (b - a).length)
        zero = arc[k // 2]
        arc = [a - zero for a in arc]
        out = []
        for i in range(n + 1):
            target = length * (i / n - 0.5)
            j = next((j for j in range(k) if arc[j + 1] >= target), k - 1)
            f = (target - arc[j]) / (arc[j + 1] - arc[j]) if arc[j + 1] > arc[j] else 0.0
            out.append(ts[j] + (ts[j + 1] - ts[j]) * min(max(f, 0.0), 1.0))
        return out

    nu, nv = max(1, math.ceil(width / step)), max(1, math.ceil(height / step))
    us = wrap(lambda t: c0 + u0 * t, width, nu)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    grid = []
    for s in us:
        vs = wrap(lambda t, s=s: c0 + u0 * s + v0 * t, height, nv)
        col = []
        for t in vs:
            hit, normal = cast(c0 + u0 * s + v0 * t)
            col.append(bm.verts.new(hit + normal * lift) if hit is not None else None)
        grid.append(col)
    for i in range(nu):
        for j in range(nv):
            if None in (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]):
                continue
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / nu, b / nv)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    if not bm.faces:
        raise ValueError(f"decal {name}: nothing of it lands on {host.name}")
    obj = _object(name, bm, material, Matrix(), parent, smooth=True)
    obj.vertex_groups.new(name="back").add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    return obj
