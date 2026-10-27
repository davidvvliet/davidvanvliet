# Review rig: lights, four cameras and the contact sheet (2x2: front, three-quarter /
# side, top). The orthographic views get a metric grid drawn behind the model, so
# proportions can be read straight off the sheet.
import math, os
import bpy
import numpy as np
from mathutils import Matrix, Vector

COLLECTION = "Rig"
VIEW_PX = 512                     # each view; the sheet is 2x this square
BG = 0.035                        # sheet background (sRGB value)
GRID, GRID_AXIS = 0.13, 0.30      # grid line and origin line brightness
GRID_STEPS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50)
GRID_MIN_PX = 24                  # finest grid whose lines are at least this far apart

def _collection():
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(col)
    return col

def clear():
    for obj in list(_collection().objects):
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            (bpy.data.cameras if isinstance(data, bpy.types.Camera) else bpy.data.lights).remove(data)

def bounds(objs):
    """World-space (min, max) over the evaluated geometry of `objs`."""
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((math.inf,) * 3), Vector((-math.inf,) * 3)
    for obj in objs:
        ev = obj.evaluated_get(dg)
        mesh = ev.to_mesh()
        mw = ev.matrix_world
        for v in mesh.vertices:
            p = mw @ v.co
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
        ev.to_mesh_clear()
    return lo, hi

def _setup_scene():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = VIEW_PX
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 16
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.color = (0.05, 0.05, 0.06)  # ambient fill on the shadow side
    if world.node_tree:
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg:
            bg.inputs["Color"].default_value = (0.05, 0.05, 0.06, 1)
            bg.inputs["Strength"].default_value = 1.0
    col = _collection()
    for name, energy, direction in (("Key", 4.0, (-1.0, 1.2, -1.4)), ("Fill", 0.8, (1.2, -0.4, 0.3))):
        light = bpy.data.lights.new(name, "SUN")
        light.energy = energy
        obj = bpy.data.objects.new(name, light)
        obj.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(obj)

# name: (direction the camera looks, its up vector, orthographic)
VIEWS = {
    "front": (Vector((0, 1, 0)), "Z", True),
    "three_quarter": (Vector((-1, 1, -0.6)).normalized(), "Z", False),
    "side": (Vector((-1, 0, 0)), "Z", True),
    "top": (Vector((0, 0, -1)), "Y", True),
}
SHEET_LAYOUT = (("front", "three_quarter"), ("side", "top"))  # rows, top to bottom

def _aim(look, world_up):
    """Rotation whose -Z is `look` and whose +Y is as close to `world_up` as possible."""
    right = look.cross(world_up).normalized()
    up = right.cross(look).normalized()
    return Matrix((right, up, -look)).transposed().to_4x4()

def _camera(view, center, radius, extents):
    look, up, ortho = VIEWS[view]
    cam = bpy.data.cameras.new(f"Cam_{view}")
    obj = bpy.data.objects.new(f"Cam_{view}", cam)
    _collection().objects.link(obj)
    cam.clip_start, cam.clip_end = radius * 0.01, radius * 20
    obj.matrix_world = _aim(look, Vector((0, 0, 1)) if up == "Z" else Vector((0, 1, 0)))
    if ortho:
        cam.type = "ORTHO"
        cam.ortho_scale = max(extents) * 1.15
        obj.location = center - look * radius * 4
    else:
        cam.lens = 50
        fov = 2 * math.atan(cam.sensor_width / (2 * cam.lens))
        obj.location = center - look * (radius * 0.9 / math.sin(fov / 2))
    bpy.context.view_layer.update()
    return obj

def _visible_extents(look, size):
    # Of the box size, the two axes perpendicular to the view direction.
    return [s for s, a in zip(size, look) if abs(a) < 0.5] or [max(size)]

def _load(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    bpy.data.images.remove(img)
    return arr.reshape(h, w, 4)  # rows bottom-up, as Blender stores them

def save_png(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)

def _grid(cam, center):
    """Background with metric grid lines for an orthographic camera; returns (rgb, step)."""
    scale = cam.data.ortho_scale
    px_per_m = VIEW_PX / scale
    step = next((s for s in GRID_STEPS if s * px_per_m >= GRID_MIN_PX), GRID_STEPS[-1])
    rgb = np.full((VIEW_PX, VIEW_PX), BG, dtype=np.float32)
    mw = cam.matrix_world
    right, up = mw.col[0].xyz.normalized(), mw.col[1].xyz.normalized()
    cam_pos = mw.translation
    for axis, vec in ((1, right), (0, up)):  # axis 1: columns (x), axis 0: rows (y)
        c = cam_pos.dot(vec)                # world coordinate at the image centre
        lo = c - scale / 2
        k0, k1 = math.ceil(lo / step), math.floor((lo + scale) / step)
        for k in range(k0, k1 + 1):
            p = int(round((k * step - lo) * px_per_m))
            if 0 <= p < VIEW_PX:
                val = GRID_AXIS if k == 0 else GRID
                if axis == 1:
                    rgb[:, p] = np.maximum(rgb[:, p], val)
                else:
                    rgb[p, :] = np.maximum(rgb[p, :], val)
    return rgb, step

def contact_sheet(objs, out_dir, frame=None):
    """Render the four views of `objs` and tile them; returns info for the status file.
    `frame` ({"min": [x, y, z], "max": [...]}) fixes the framing, so a probe's sheet and its
    reference sheet line up exactly; otherwise the views fit `objs`."""
    clear()
    _setup_scene()
    scene = bpy.context.scene
    lo, hi = (Vector(frame["min"]), Vector(frame["max"])) if frame else bounds(objs)
    center, size = (lo + hi) / 2, hi - lo
    radius = max(size.length / 2, 1e-3)
    os.makedirs(os.path.join(out_dir, "views"), exist_ok=True)
    tiles, grids = {}, {}
    rig = set(_collection().objects)
    hidden = [o for o in scene.objects if o.type in ("MESH", "LIGHT") and o not in objs
              and o not in rig and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    try:
        for view, (look, _, ortho) in VIEWS.items():
            cam = _camera(view, center, radius, _visible_extents(look, size))
            scene.camera = cam
            path = os.path.join(out_dir, "views", f"{view}.png")
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            rgba = _load(path)
            if ortho:
                bg, step = _grid(cam, center)
                grids[view] = step
            else:
                bg = np.full(rgba.shape[:2], BG, dtype=np.float32)
            a = rgba[..., 3:4]
            tile = np.ones_like(rgba)
            tile[..., :3] = rgba[..., :3] * a + bg[..., None] * (1 - a)
            tiles[view] = tile
    finally:
        for o in hidden:
            o.hide_render = False
    rows = [np.concatenate([tiles[v] for v in row], axis=1) for row in SHEET_LAYOUT]
    sheet = np.concatenate(rows[::-1], axis=0)  # bottom-up storage: last row first
    path = os.path.join(out_dir, "sheet.png")
    save_png(sheet, path)
    return {"sheet": path, "grid_m": grids, "size_m": [round(s, 4) for s in size]}

def compare(a_path, b_path):
    """Mean absolute RGB difference (0..1) between two sheets, or None if not comparable."""
    if not (os.path.exists(a_path) and os.path.exists(b_path)):
        return None
    a, b = _load(a_path), _load(b_path)
    if a.shape != b.shape:
        return 1.0
    return float(np.abs(a[..., :3] - b[..., :3]).mean())

CLOSEUP_PX = 512

def closeups(objs, out_dir, views=None):
    """Perspective close-ups for checking joints and small parts at a readable size.
    `views`: [{"name", "target": [x, y, z], "look": [x, y, z], "radius": m}] from the spec;
    without them, one view of the craft's core (every part but the long booms and rods)."""
    scene = bpy.context.scene
    if not views:
        lo, hi = bounds(objs)
        span = (hi - lo).length
        core = [o for o in objs if max(o.dimensions) < span * 0.25] or objs
        clo, chi = bounds(core)
        views = [{"name": "core", "target": list((clo + chi) / 2), "look": [-1, 1, -0.6],
                  "radius": max((chi - clo).length / 2, 0.05)}]
    os.makedirs(os.path.join(out_dir, "closeups"), exist_ok=True)
    keep = (scene.render.resolution_x, scene.render.resolution_y, scene.render.film_transparent)
    scene.render.resolution_x = scene.render.resolution_y = CLOSEUP_PX
    scene.render.film_transparent = False  # opaque: the world colour is the background
    names = []
    hidden = [o for o in scene.objects if o.type in ("MESH", "LIGHT") and o not in objs
              and o not in set(_collection().objects) and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    try:
        for v in views:
            look = Vector(v["look"]).normalized()
            cam = bpy.data.cameras.new(f"Close_{v['name']}")
            obj = bpy.data.objects.new(f"Close_{v['name']}", cam)
            _collection().objects.link(obj)
            up = Vector((0, 0, 1)) if abs(look.z) < 0.95 else Vector((0, 1, 0))
            obj.matrix_world = _aim(look, up)
            cam.lens = 50
            fov = 2 * math.atan(cam.sensor_width / (2 * cam.lens))
            dist = v["radius"] * 1.1 / math.sin(fov / 2)
            obj.location = Vector(v["target"]) - look * dist
            cam.clip_start, cam.clip_end = dist * 0.01, dist * 50
            bpy.context.view_layer.update()
            scene.camera = obj
            scene.render.filepath = os.path.join(out_dir, "closeups", f"{v['name']}.png")
            bpy.ops.render.render(write_still=True)
            names.append(v["name"])
    finally:
        for o in hidden:
            o.hide_render = False
        scene.render.resolution_x, scene.render.resolution_y, scene.render.film_transparent = keep
    # One image to review: tiles three to a row, in spec order, top-left first.
    tiles = [_load(os.path.join(out_dir, "closeups", f"{n}.png")) for n in names]
    cols = min(3, len(tiles))
    blank = np.empty_like(tiles[0])
    blank[:] = tiles[0][0, 0]  # fill spare tiles with the background, not black
    while len(tiles) % cols:
        tiles.append(blank)
    rows = [np.concatenate(tiles[i:i + cols], axis=1) for i in range(0, len(tiles), cols)]
    save_png(np.concatenate(rows[::-1], axis=0), os.path.join(out_dir, "closeups.png"))
    return names
