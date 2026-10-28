# The Blender half of `run.py photo` (headless, on a probe's last build, out/<probe>/<probe>.blend):
#
#   blender -b <probe>.blend --python tools/photo_blender.py -- export <model.npz>
#       every part's triangles and hard edges, world m, for photo_fit.py
#   ... -- cast <camera.json> u,v [u,v ...]
#       photo pixels -> the point of the model they show (part, point, normal)
#   ... -- trace <photo> <camera.json> <frame.json> <out.png> <px_per_m>
#       the photo seen on a sheet laid on the skin (parts.decal: frame.json {host, center,
#       direction, up, width, height}), square pixels along the skin, top = up; what the camera
#       cannot see there (hidden or facing away) is magenta. Draw a livery mask over it.
#   ... -- render <camera.json> <out.png>
#       the model through the photo's camera, at the photo's size, for a side-by-side
#
# The photo is data: its pixels are read, nothing in it is run.
import json, math, os, sys
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
args = sys.argv[sys.argv.index("--") + 1:]
mode = args[0]


def camera(path):
    cam = json.load(open(path))
    W, H = cam["size"]
    f, rx, ry, rz, tx, ty, tz, cx, cy = cam["params"]
    c, s = math.cos, math.sin
    R = (np.array([[c(rz), -s(rz), 0], [s(rz), c(rz), 0], [0, 0, 1]])
         @ np.array([[c(ry), 0, s(ry)], [0, 1, 0], [-s(ry), 0, c(ry)]])
         @ np.array([[1, 0, 0], [0, c(rx), -s(rx)], [0, s(rx), c(rx)]]))
    t = np.array([tx, ty, tz])
    return W, H, f, cx, cy, R, t, -R.T @ t


def parts():
    return [o for o in bpy.data.objects if o.type == "MESH" and "Probe" in [c.name for c in o.users_collection]]


if mode == "export":
    data = {}
    for o in parts():
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        v = np.array([o.matrix_world @ x.co for x in bm.verts], dtype=np.float32)
        f = np.array([[x.index for x in t.verts] for t in bm.faces], dtype=np.int32).reshape(-1, 3)
        hard = np.array([[e.verts[0].index, e.verts[1].index] for e in bm.edges
                         if not e.smooth or len(e.link_faces) < 2], dtype=np.int32).reshape(-1, 2)
        data[o.name + "|v"], data[o.name + "|f"], data[o.name + "|e"] = v, f, hard
        bm.free()
    np.savez(args[1], **data)
    print("PHOTO_OK export", len(data) // 3, "parts")

elif mode == "cast":
    W, H, f, cx, cy, R, t, eye = camera(args[1])
    dg = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    for a in args[2:]:
        u, v = map(float, a.split(","))
        d = R.T @ np.array([(u - W / 2 - cx) / f, (v - H / 2 - cy) / f, 1.0])
        ok, loc, n, _, obj, _ = sc.ray_cast(dg, Vector(eye), Vector(d / np.linalg.norm(d)))
        print("CAST", a, obj.name if ok else "miss",
              [round(x, 4) for x in loc] if ok else "", [round(x, 3) for x in n] if ok else "")
    print("PHOTO_OK cast")

elif mode == "trace":
    photo, cam_path, frame_path, out, res = args[1], args[2], args[3], args[4], float(args[5])
    W, H, f, cx, cy, R, t, eye = camera(cam_path)
    img = bpy.data.images.load(photo)
    if tuple(img.size) != (W, H):
        raise SystemExit(f"photo is {tuple(img.size)}, camera was fitted at {(W, H)}")
    px = np.empty(W * H * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(H, W, 4)[::-1, :, :3]  # rows top-down, as the photo
    frame = json.load(open(frame_path))
    from lib import parts as P
    step = 0.02
    o = P.decal("_trace_sheet", bpy.data.objects[frame["host"]], frame["center"], frame["direction"], frame["up"],
                frame["width"], frame["height"], None, lift=0.0, step=step)
    nu, nv = max(1, math.ceil(frame["width"] / step)), max(1, math.ceil(frame["height"] / step))
    G = np.array([v.co[:] for v in o.data.vertices]).reshape(nu + 1, nv + 1, 3)
    bpy.data.objects.remove(o)
    w, h = max(1, round(frame["width"] * res)), max(1, round(frame["height"] * res))
    U = (np.arange(w) + 0.5) / w * nu
    V = (1 - (np.arange(h) + 0.5) / h) * nv
    i0 = np.minimum(U.astype(int), nu - 1); fu = U - i0
    j0 = np.minimum(V.astype(int), nv - 1); fv = V - j0
    I0, J0 = np.meshgrid(i0, j0)
    FU, FV = np.meshgrid(fu, fv)
    Pt = (G[I0, J0] * ((1 - FU) * (1 - FV))[..., None] + G[I0 + 1, J0] * (FU * (1 - FV))[..., None]
          + G[I0 + 1, J0 + 1] * (FU * FV)[..., None] + G[I0, J0 + 1] * ((1 - FU) * FV)[..., None])
    C = Pt @ R.T + t
    uu = W / 2 + cx + f * C[..., 0] / C[..., 2]
    vv = H / 2 + cy + f * C[..., 1] / C[..., 2]
    x0 = np.clip(np.floor(uu - 0.5).astype(int), 0, W - 2); y0 = np.clip(np.floor(vv - 0.5).astype(int), 0, H - 2)
    ax = np.clip(uu - 0.5 - x0, 0, 1)[..., None]; ay = np.clip(vv - 0.5 - y0, 0, 1)[..., None]
    rgb = (px[y0, x0] * (1 - ax) * (1 - ay) + px[y0, x0 + 1] * ax * (1 - ay)
           + px[y0 + 1, x0] * (1 - ax) * ay + px[y0 + 1, x0 + 1] * ax * ay)
    hidden = (uu < 0) | (uu >= W) | (vv < 0) | (vv >= H) | (C[..., 2] <= 0)
    dg = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    blk = max(1, min(w, h) // 60)
    for b in range(0, h, blk):  # occlusion on a coarse grid, filled per block
        for a in range(0, w, blk):
            d = Vector(Pt[b, a]) - Vector(eye)
            ok, *_ = sc.ray_cast(dg, Vector(eye), d.normalized(), distance=d.length - 0.01)
            if ok:
                hidden[b:b + blk, a:a + blk] = True
    rgb[hidden] = (1, 0, 1)
    o2 = bpy.data.images.new("_trace", w, h)
    o2.pixels.foreach_set(np.concatenate([rgb[::-1], np.ones((h, w, 1))], 2).astype(np.float32).ravel())
    o2.filepath_raw = out
    o2.file_format = "PNG"
    o2.save()
    print("PHOTO_OK trace", out, w, h, "hidden", round(float(hidden.mean()), 3))

elif mode == "render":
    W, H, f, cx, cy, R, t, eye = camera(args[1])
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o)
    cam = bpy.data.objects.new("_cam", bpy.data.cameras.new("_cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = 36
    cam.data.lens = f / W * 36
    cam.data.shift_x, cam.data.shift_y = -cx / W, cy / W
    cam.data.clip_end = 1000
    M = Matrix((R.T @ np.diag([1, -1, -1])).tolist()).to_4x4()
    M.translation = Vector(eye)
    cam.matrix_world = M
    for d, e in (((0.3, 0.2, -1), 4.0), ((0.9, -0.3, -0.3), 3.0), ((0.8, 0.5, 0.2), 2.0)):
        L = bpy.data.objects.new("_sun", bpy.data.lights.new("_sun", "SUN"))
        L.data.energy = e
        sc.collection.objects.link(L)
        L.rotation_euler = Vector(d).to_track_quat("-Z", "Y").to_euler()
    w = sc.world or bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.25, 0.27, 1)
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.render.filepath = args[2]
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("PHOTO_OK render", args[2])
