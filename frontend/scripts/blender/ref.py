# Measures a reference model (e.g. NASA 3D Resources) headless: imports it, bakes every
# transform so units are world metres, renders it through the review rig (same four
# views and grid as our builds) and lists its largest separate pieces with sizes and
# main-axis lengths. `run.py ref <probe> <model>` starts Blender with this file.
# Output: refs/<probe>/reference-sheet.png and out/<probe>/ref/parts.json.
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy
import numpy as np
from lib import rig

PIECES_LISTED = 60

def _import(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    else:
        raise ValueError(f"unsupported reference format {ext}")

def _bake():
    """Unparent everything keeping world transforms, drop empty helpers, apply transforms."""
    objs = list(bpy.context.scene.objects)
    for o in objs:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in objs:
        if o.type != "MESH" or len(o.data.vertices) <= 8 and not o.data.polygons:
            bpy.data.objects.remove(o)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    # glTF helpers: a bare unit cube with no material that only carried the root scale
    for o in list(meshes):
        if not o.material_slots and len(o.data.vertices) == 24 and max(o.dimensions) == 1.0:
            meshes.remove(o)
            bpy.data.objects.remove(o)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return meshes

def _points(o):
    co = np.empty(len(o.data.vertices) * 3)
    o.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)

def _pieces(meshes):
    """Every loose piece: size, centre, and length along its main axis."""
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    rows = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or not len(o.data.vertices):
            continue
        p = _points(o)
        c = p.mean(0)
        axis = np.linalg.svd(p - c, full_matrices=False)[2][0] if len(p) > 1 else np.array([0, 0, 1.0])
        t = (p - c) @ axis
        rows.append({"material": o.active_material.name if o.active_material else None,
                     "verts": len(p), "size": np.round(p.max(0) - p.min(0), 3).tolist(),
                     "centre": np.round((p.max(0) + p.min(0)) / 2, 3).tolist(),
                     "main_axis": np.round(axis, 3).tolist(), "main_length": round(float(t.max() - t.min()), 3)})
    rows.sort(key=lambda r: -r["main_length"])
    return rows

def main(probe, path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _import(path)
    meshes = _bake()
    P = np.concatenate([_points(o) for o in meshes])
    tris = 0
    for o in meshes:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    out = os.path.join(HERE, "out", probe, "ref")
    os.makedirs(out, exist_ok=True)
    sheet = rig.contact_sheet(meshes, out)
    refs = os.path.join(HERE, "refs", probe)
    os.makedirs(refs, exist_ok=True)
    shutil.copy(sheet["sheet"], os.path.join(refs, "reference-sheet.png"))
    pieces = _pieces(meshes)
    report = {"model": os.path.basename(path), "triangles": tris,
              "size_m": np.round(P.max(0) - P.min(0), 3).tolist(),
              "min_m": np.round(P.min(0), 3).tolist(), "max_m": np.round(P.max(0), 3).tolist(),
              "grid_m": sheet["grid_m"], "pieces": len(pieces), "largest_pieces": pieces[:PIECES_LISTED]}
    with open(os.path.join(out, "parts.json"), "w") as f:
        json.dump(report, f, indent=1)
    print("REF_OK " + json.dumps({k: v for k, v in report.items() if k != "largest_pieces"}))

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    main(args[0], args[1])
