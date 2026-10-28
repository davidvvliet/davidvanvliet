# Close-ups of a reference model (top row) and our built probe (bottom row) from the same
# cameras, in one image (Blender script; run through `run.py compare`). Textures shown as
# they are, so missing parts, wrong shapes and badly projected bake texture stand out.
#
#   blender -b --python tools/compare.py -- <reference> <ours.glb> <out.png> <view> [<view> ...]
#
# A view is "tx,ty,tz,dx,dy,dz": the camera looks at the target from target + (dx, dy, dz),
# z up, 50 mm lens. A reference object named '_root' (NASA's untextured placeholder box) is
# hidden. The models are data: imported, never executed.
import os, sys, tempfile
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces import _import  # noqa: E402

TILE = 500

def _render(model, views, tmp, tag):
    _import(model)
    sc = bpy.context.scene
    if "_root" in bpy.data.objects:
        bpy.data.objects["_root"].hide_render = True
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    sc.render.resolution_x = sc.render.resolution_y = TILE
    cam = bpy.data.cameras.new("cam"); cam.lens = 50
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co)
    sc.camera = co
    tiles = []
    for i, (target, offset) in enumerate(views):
        co.location = target + offset
        co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(tmp, f"{tag}{i}.png")
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(sc.render.filepath)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(TILE, TILE, 4)
        tiles.append(px)
    return tiles

def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    if len(a) < 4:
        raise SystemExit("usage: compare.py -- <reference> <ours.glb> <out.png> tx,ty,tz,dx,dy,dz [...]")
    ref, ours, out = a[0], a[1], a[2]
    views = []
    for v in a[3:]:
        n = [float(x) for x in v.split(",")]
        if len(n) != 6:
            raise SystemExit(f"view {v!r}: need tx,ty,tz,dx,dy,dz")
        views.append((Vector(n[:3]), Vector(n[3:])))
    with tempfile.TemporaryDirectory() as tmp:
        top = _render(ref, views, tmp, "ref")
        bottom = _render(ours, views, tmp, "ours")
    # Blender image rows run bottom-up: the bottom row of the sheet comes first.
    sheet = np.concatenate([np.concatenate(bottom, axis=1), np.concatenate(top, axis=1)], axis=0)
    h, w = sheet.shape[:2]
    img = bpy.data.images.new("compare", width=w, height=h, alpha=True)
    img.pixels = sheet.ravel()
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    print("COMPARE_OK", out)

main()
