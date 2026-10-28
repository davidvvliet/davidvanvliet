# Renders a reference model's loose pieces in a box region, each in its own colour, and
# prints a legend (Blender script; run through `run.py idview`). For telling which of
# hundreds of untitled pieces is which part.
#
#   blender -b --python tools/idview.py -- <model> <out.png> x0 y0 z0 x1 y1 z1
#           tx ty tz dx dy dz
#
# The camera looks at the target (tx, ty, tz) from target + (dx, dy, dz), z up. Each legend
# line: ID, its colour (0-255 RGB), bounds centre and size, vertex count. The model is data:
# it is imported, never executed.
import colorsys, os, sys
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces import _import  # noqa: E402  (same folder; pieces.py's main() only runs under its own name)

def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    if len(a) != 14:
        raise SystemExit("usage: idview.py -- <model> <out.png> x0 y0 z0 x1 y1 z1 tx ty tz dx dy dz")
    model, out = a[0], a[1]
    lo, hi = np.array([float(x) for x in a[2:5]]), np.array([float(x) for x in a[5:8]])
    target, offset = Vector([float(x) for x in a[8:11]]), Vector([float(x) for x in a[11:14]])
    _import(model)
    sc = bpy.context.scene
    for o in [o for o in sc.objects if o.type == "MESH"]:
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.separate(type="LOOSE")
        bpy.ops.object.mode_set(mode="OBJECT")
    k = 0
    for o in sorted([o for o in sc.objects if o.type == "MESH"], key=lambda o: o.name):
        P = np.array([v.co[:] for v in o.data.vertices])
        c = (P.min(0) + P.max(0)) / 2
        if not np.all((c > lo) & (c < hi)):
            o.hide_render = True
            continue
        k += 1
        col = colorsys.hsv_to_rgb((k * 0.61803) % 1, 0.8, 1.0)   # golden-ratio hues stay apart
        o.color = (*col, 1)
        print(f"ID {k}  rgb {tuple(int(x * 255) for x in col)}  centre {np.round(c, 3).tolist()}  "
              f"size {np.round(P.max(0) - P.min(0), 3).tolist()}  v{len(P)}")
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "OBJECT"
    sc.render.resolution_x = sc.render.resolution_y = 900
    cam = bpy.data.cameras.new("cam"); cam.lens = 35
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co)
    co.location = target + offset
    co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = co
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("IDVIEW_OK", out)

main()
