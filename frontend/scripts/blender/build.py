# Builds one probe inside Blender: run its script, check it against its spec, render
# the contact sheet, export the .glb, and record it all in out/status.json (read by the
# /models dashboard). Runs headless (`run.py build <probe>` starts Blender with this
# file) or in the live session (`run.py` sends `build(<probe>)` to it).
import datetime as dt, importlib, importlib.util, json, os, shutil, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SPECS, PROBES, BASELINES = (os.path.join(HERE, d) for d in ("specs", "probes", "baselines"))
STATUS = os.path.join(OUT, "status.json")
HISTORY_KEEP = 20
BASELINE_TOLERANCE = 0.01  # mean RGB difference above which a sheet counts as changed

if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy

def _lib():
    # Reload so the live session picks up edits to the library without a restart.
    from lib import materials, parts, rig, checks, textures, sources, bake, published, livery
    for m in (sources, materials, textures, parts, rig, checks, bake, published, livery):
        importlib.reload(m)
    return parts, rig, checks

def read_status():
    try:
        with open(STATUS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"current": None, "probes": {}}

def _write_status(status):
    os.makedirs(OUT, exist_ok=True)
    status["updated"] = time.time()
    tmp = STATUS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(status, f, indent=1)
    os.replace(tmp, STATUS)

def _step(status, probe, step, state="running", message=None):
    status["current"] = {"probe": probe, "step": step, "state": state, "message": message,
                         "session": "headless" if bpy.app.background else "live", "at": time.time()}
    _write_status(status)
    print(f"[{probe}] {step}" + (f": {message}" if message else ""), flush=True)

# Each build replaces the probe's last entry. Only the approval carries over; a failed
# build also keeps the last good sheet and export to look at, but not their checks.
CARRY = ("approved",)
CARRY_ON_FAILURE = ("sheet", "glb", "history", "grid_m", "size_m", "baseline", "closeups")

def _carry(status, probe, entry, failed):
    prev = status.get("probes", {}).get(probe, {})
    keep = CARRY + (CARRY_ON_FAILURE if failed else ())
    return {**{k: prev[k] for k in keep if k in prev and k not in entry}, **entry}

def _load_probe(name):
    path = os.path.join(PROBES, f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"probe_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def build(probe, export=True):
    """Build `probe`; returns its status entry (also written to out/status.json)."""
    status = read_status()
    out_dir = os.path.join(OUT, probe)
    os.makedirs(out_dir, exist_ok=True)
    started = time.time()
    entry = {"started": started}
    try:
        parts, rig, checks = _lib()
        # What this build reads, taken before it starts: approve refuses the build when the repo
        # has changed since (see lib/published.py).
        from lib import published
        entry["inputs"] = published.inputs(probe)
        _step(status, probe, "spec")
        with open(os.path.join(SPECS, f"{probe}.json")) as f:
            spec = json.load(f)
        entry["title"] = spec.get("title", probe)

        _step(status, probe, "model")
        from lib import materials
        material_problems = materials.use(spec.get("materials"))
        parts.clear()
        _load_probe(probe).build(spec)
        all_objs = list(parts.collection().objects)  # parts and joints
        # The spec's joint limits travel with the model (glTF extras) for viewers: a joint with
        # "move_to" turns to that angle when its part is clicked, with every joint in its "group".
        for jname, j in spec.get("joints", {}).items():
            jo = bpy.data.objects.get(jname)
            if jo is not None and "joint_axis" in jo:
                for k in ("min", "max", "move_to", "group"):
                    if k in j:
                        jo[f"joint_{k}"] = j[k]
        objs = parts.meshes(all_objs)
        if not objs:
            raise RuntimeError("the probe script built no objects")
        baked = None
        if spec.get("bake"):  # colours baked from the reference model (run.py bake)
            from lib import bake
            jpg, info = bake.paths(HERE, probe)
            bake.unwrap(objs)
            baked = bake.stale(objs, info) if os.path.exists(jpg) else "no baked.jpg: run `run.py bake`"
            if os.path.exists(jpg):
                bake.apply(objs, jpg, bake.normal_path(HERE, probe))
        painted = None
        if spec.get("livery"):  # markings baked into the skin texture (lib/livery.py)
            from lib import livery
            painted = livery.paint(spec, objs, HERE, probe, unwrapped=bool(spec.get("bake")))

        _step(status, probe, "checks")
        results = checks.run(spec, all_objs)
        if spec.get("bake"):
            results.append({"name": "bake", "ok": baked is None, "measured": "fresh" if baked is None else "stale",
                            "expected": "baked for this geometry", "unit": "", "detail": baked or "atlas matches the parts"})
        if painted is not None:
            results.append(painted)
        from lib import sources
        src = sources.check(spec)
        results.append({"name": "sources", "ok": not src, "measured": "ok" if not src else "off",
                        "expected": "listed, cited", "unit": "",
                        "detail": "; ".join(src) or "every source cited, every citation listed, saved files present"})

        _step(status, probe, "render")
        entry.update(rig.contact_sheet(objs, out_dir, spec.get("sheet_frame")))
        entry["closeups"] = rig.closeups(objs, out_dir, spec.get("closeups"))
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        hist = os.path.join(out_dir, "history")
        os.makedirs(hist, exist_ok=True)
        shutil.copy(entry["sheet"], os.path.join(hist, f"{stamp}.png"))
        for old in sorted(os.listdir(hist))[:-HISTORY_KEEP]:
            os.remove(os.path.join(hist, old))
        entry["history"] = sorted(os.listdir(hist))
        diff = rig.compare(entry["sheet"], os.path.join(BASELINES, f"{probe}.png"))
        entry["baseline"] = None if diff is None else {"diff": round(diff, 5), "changed": diff > BASELINE_TOLERANCE}

        if export:
            _step(status, probe, "export")
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            for o in all_objs:
                o.select_set(True)
            glb = os.path.join(out_dir, f"{probe}.glb")
            # Extras carry each part's assembly (and joints' axes) to the dashboard.
            bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True,
                                      export_apply=True, export_yup=True, export_extras=True,
                                      export_image_quality=90)
            entry["glb"] = glb
            results.append(checks.file_size(glb, spec))
            tex = checks.textures(objs, glb)
            if tex is not None:
                results.append({"name": "textures", "ok": not tex, "measured": "ok" if not tex else "broken",
                                "expected": "images + UVs", "unit": "",
                                "detail": "; ".join(tex) or "images present, UVs inside, all exported"})
            mat = checks.materials(spec, objs, glb, material_problems)
            results.append({"name": "materials", "ok": not mat, "measured": "ok" if not mat else "off",
                            "expected": "sourced, exported", "unit": "",
                            "detail": "; ".join(mat) or "spec materials sourced; colour, metal, roughness exported as built"})
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, f"{probe}.blend"), copy=True)

        entry["checks"] = results
        entry["ok"] = all(r["ok"] for r in results)
        entry["seconds"] = round(time.time() - started, 1)
        failed = [r["name"] for r in results if not r["ok"]]
        status.setdefault("probes", {})[probe] = _carry(status, probe, entry, failed=False)
        _step(status, probe, "done", "done" if not failed else "failed",
              "all checks pass" if not failed else "failing: " + ", ".join(failed))
    except Exception as e:
        entry.update(ok=False, error="".join(traceback.format_exception(e)))
        status.setdefault("probes", {})[probe] = _carry(status, probe, entry, failed=True)
        _step(status, probe, "error", "failed", f"{type(e).__name__}: {e}")
        if bpy.app.background:
            raise
    return status["probes"][probe]

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        sys.exit("usage: blender --background --python build.py -- <probe> [--no-export]")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = build(args[0], export="--no-export" not in args)
    sys.exit(0 if result.get("ok") else 1)
