#!/usr/bin/env python3
# Command line for the probe-modelling harness (plain Python 3; `photo` also needs numpy and Pillow).
#
#   run.py blender                  open Blender with the live server
#   run.py build <probe>            build in the live session if one is open, else headless
#          [--headless] [--no-export]
#   run.py all [--headless]         rebuild every probe; fails on a failing check or a
#                                   sheet that changed against its approved baseline
#   run.py approve <probe> [--force] copy the last build to public/models (with a thumbnail) and make its
#                                   sheet the baseline
#   run.py new <probe> ["Title"]    start a probe from the templates
#   run.py ref <probe> <model>      measure a reference model: sheet + largest pieces
#   run.py explode <probe> <model>  break the reference model into our parts: per-part
#                                   comparison and the pieces none of our parts claim
#   run.py pieces <model> x0 y0 z0 x1 y1 z1 [--min M] [--max M] [--struts] [--dump]
#                                   list a reference model's loose pieces in a region
#                                   (tools/pieces.py): sizes, strut end points, vertices
#   run.py idview <model> <out.png> x0 y0 z0 x1 y1 z1 tx ty tz dx dy dz
#                                   render the pieces in a region one colour each, with a legend
#   run.py compare <probe> <reference> <out.png> tx,ty,tz,dx,dy,dz ...
#                                   close-ups of the reference (top) and our last build (bottom)
#   run.py photo get <probe> <NASM id | url> ...
#                                   photos of the real vehicle at full size into out/<probe>/photos
#                                   (Smithsonian ids at the largest size served); listed in
#                                   refs/<probe>/photos/photos.json so they can be fetched again
#   run.py photo fit <probe> <photo>   fit a camera to a photo from refs/<probe>/photos/<photo>.fit.json
#                                   (after a build): <photo>.camera.json there, and an overlay
#   run.py photo view <probe> <photo>  the last build through the photo's camera, beside the photo
#   run.py photo trace <probe> <photo> <frame.json> <out.png> [px_per_m]
#                                   the photo flattened onto a sheet of skin (as a livery marking's
#                                   frame), for drawing its mask
#   run.py photo cast <probe> <photo> u,v ...  photo pixels -> points on the model
#   run.py dev [probe] [--headless] rebuild on every save of a probe script, spec or lib/
#   run.py send <file.py | ->       run Python in the live session
#   run.py status                   print the last build of every probe, and whether its
#                                   published version is behind the repo
#   run.py watch                    show each new contact sheet in iTerm2 (imgcat)
import glob, json, math, os, re, shutil, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(os.path.dirname(HERE))
PUBLIC_MODELS = os.path.join(FRONTEND, "public", "models")
MODEL_CREDITS = os.path.join(FRONTEND, "app", "terminal", "commands", "model-credits.json")
OUT = os.path.join(HERE, "out")
STATUS = os.path.join(OUT, "status.json")
CONFIG = json.load(open(os.path.join(HERE, "blender.json")))
BLENDER = os.environ.get("BLENDER_PATH", CONFIG["path"])
PORT = CONFIG.get("port", 9876)

def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)

def check_version():
    if not os.path.exists(BLENDER):
        die(f"Blender not found at {BLENDER} (set BLENDER_PATH or edit blender.json)")
    out = subprocess.run([BLENDER, "--version"], capture_output=True, text=True).stdout
    m = re.search(r"Blender (\d+\.\d+\.\d+)", out)
    if m and m.group(1) != CONFIG["version"]:
        print(f"warning: Blender {m.group(1)} installed, harness pinned to {CONFIG['version']}"
              " (renders and exports may differ from the baselines)", file=sys.stderr)

def read_status():
    try:
        return json.load(open(STATUS))
    except (OSError, ValueError):
        return {"current": None, "probes": {}}

def probes():
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(HERE, "specs", "*.json")))

# --- live session ---------------------------------------------------------------

def live_available():
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=0.3).close()
        return True
    except OSError:
        return False

def live_here():
    """A live session that serves this checkout. Another worktree's session would build its own files."""
    if not live_available():
        return False
    try:
        reply = send("import build as _b, os; print(os.path.realpath(os.path.dirname(_b.__file__)))", timeout=10)
        return reply["ok"] and reply["output"].strip() == os.path.realpath(HERE)
    except (OSError, ValueError, KeyError):
        return False

def send(code, timeout=600):
    with socket.create_connection(("127.0.0.1", PORT), timeout=timeout) as s:
        s.sendall(code.encode())
        s.shutdown(socket.SHUT_WR)
        chunks = []
        while data := s.recv(65536):
            chunks.append(data)
    return json.loads(b"".join(chunks).decode())

def cmd_blender(args):
    if live_available():
        print(f"A live session is already listening on port {PORT}.")
        return
    check_version()
    subprocess.Popen([BLENDER, "--python", os.path.join(HERE, "addon", "live_server.py")],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        if live_available():
            print(f"Blender is open with the live server on 127.0.0.1:{PORT}.")
            return
        time.sleep(0.5)
    die("Blender started but the live server did not answer within 30 s.")

def cmd_send(args):
    if not args:
        die("usage: run.py send <file.py | ->")
    code = sys.stdin.read() if args[0] == "-" else open(args[0]).read()
    if not live_available():
        die("No live session (start one with: run.py blender)")
    reply = send(code)
    sys.stdout.write(reply["output"])
    if not reply["ok"]:
        die(reply["error"])

# --- builds ---------------------------------------------------------------------

def print_entry(probe, entry):
    mark = "PASS" if entry.get("ok") else "FAIL"
    print(f"\n{probe}: {mark}  ({entry.get('seconds', '?')} s)")
    if entry.get("error"):
        print(entry["error"].rstrip())
    for r in entry.get("checks", []):
        unit = r.get("unit", "")
        print(f"  {'✓' if r['ok'] else '✗'} {r['name']:<22} {r['measured']} / {r['expected']} {unit}  {r.get('detail') or ''}")
    b = entry.get("baseline")
    if b is not None:
        print(f"  {'✗ changed' if b['changed'] else '✓ unchanged'} against baseline (diff {b['diff']})")
    if entry.get("sheet"):
        print(f"  sheet: {entry['sheet']}")

def build(probe, headless=False, export=True):
    if not os.path.exists(os.path.join(HERE, "specs", f"{probe}.json")):
        die(f"No spec for '{probe}'. Known: {', '.join(probes()) or 'none'} (start one with: run.py new {probe})")
    t0, log = time.time(), ""
    if not headless and live_here():
        code = (f"import importlib, build as _b; importlib.reload(_b); "
                f"_b.build({probe!r}, export={export!r})")
        reply = send(code)
        if not reply["ok"]:
            die(reply["error"])
    else:
        check_version()
        cmd = [BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
               "--python", os.path.join(HERE, "build.py"), "--", probe] + ([] if export else ["--no-export"])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        log = proc.stdout[-4000:] + proc.stderr[-4000:]
    entry = read_status().get("probes", {}).get(probe)
    if not entry or entry.get("started", 0) < t0 - 1:  # Blender died before recording this build
        die(f"Build of '{probe}' did not finish.\n{log}")
    print_entry(probe, entry)
    return entry

def cmd_build(args):
    names = [a for a in args if not a.startswith("--")]
    if len(names) != 1:
        die("usage: run.py build <probe> [--headless] [--no-export]")
    entry = build(names[0], headless="--headless" in args, export="--no-export" not in args)
    sys.exit(0 if entry.get("ok") else 1)

def cmd_all(args):
    bad = []
    for p in probes():
        entry = build(p, headless="--headless" in args)
        if not entry.get("ok") or (entry.get("baseline") or {}).get("changed"):
            bad.append(p)
    print(f"\n{len(probes()) - len(bad)}/{len(probes())} probes pass" + (f"; check: {', '.join(bad)}" if bad else ""))
    sys.exit(1 if bad else 0)

def cmd_approve(args):
    names = [a for a in args if not a.startswith("--")]
    if len(names) != 1:
        die("usage: run.py approve <probe> [--force]")
    probe = names[0]
    status = read_status()
    entry = status.get("probes", {}).get(probe)
    if not entry or not entry.get("glb") or not os.path.exists(entry["glb"]):
        die(f"No exported build of '{probe}' yet (run: run.py build {probe})")
    if not entry.get("ok") and "--force" not in args:
        die(f"The last build of '{probe}' has failing checks; fix them or pass --force.")
    # Publish only what the repo builds now: another session (or an edit since) may have changed
    # the probe's files or lib/ after the last build.
    sys.path.insert(0, HERE)
    from lib import published
    changed = published.since_build(probe, entry.get("inputs"))
    if changed is None:
        die(f"The last build of '{probe}' predates input tracking; rebuild it (run.py build {probe}), then approve.")
    if changed:
        die(f"Changed since the last build of '{probe}': {', '.join(changed)}.\n"
            f"Rebuild (run.py build {probe}), look at the result, then approve.")
    # Shared code with uncommitted edits (often another session's work in progress) would be
    # baked into this model and its fingerprint. The probe's own files may be uncommitted.
    shared = [p for p in published.inputs(probe) if not published.own(probe, p)]
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *shared], cwd=HERE,
                           capture_output=True, text=True).stdout.split("\n")
    dirty = [line[3:] for line in dirty if line.strip()]
    if dirty and "--force" not in args:
        die(f"Shared harness code has uncommitted changes: {', '.join(dirty)}.\n"
            "Commit them first (or ask the session editing them), rebuild, then approve.")
    spec = json.load(open(os.path.join(HERE, "specs", f"{probe}.json")))
    if not spec.get("fixture"):  # fixtures only guard lib/; they never ship
        os.makedirs(PUBLIC_MODELS, exist_ok=True)
        shutil.copy(entry["glb"], os.path.join(PUBLIC_MODELS, f"{probe}.glb"))
        # The /models grid shows this image until the live model has loaded.
        check_version()
        proc = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                               "--python", os.path.join(HERE, "thumbnail.py"), "--",
                               os.path.join(PUBLIC_MODELS, f"{probe}.glb"), os.path.join(PUBLIC_MODELS, f"{probe}.webp")],
                              capture_output=True, text=True)
        if "THUMB_OK" not in proc.stdout:
            die(proc.stdout[-4000:] + proc.stderr[-4000:])
        # The site's credits list what shapes a published model (its sources' "credit" lines).
        sys.path.insert(0, HERE)
        from lib import sources
        credits = json.load(open(MODEL_CREDITS)) if os.path.exists(MODEL_CREDITS) else {}
        credits[probe] = sources.credits(spec)
        with open(MODEL_CREDITS, "w") as f:
            json.dump(dict(sorted(credits.items())), f, indent=2, ensure_ascii=False)
            f.write("\n")
        published.record(probe, entry["inputs"])  # what this published model was built from
    shutil.copy(entry["sheet"], os.path.join(HERE, "baselines", f"{probe}.png"))
    entry["approved"] = time.time()
    entry["baseline"] = {"diff": 0.0, "changed": False}
    tmp = STATUS + ".tmp"
    json.dump(status, open(tmp, "w"), indent=1)
    os.replace(tmp, STATUS)
    print(f"Approved {probe}: " + ("baseline updated (fixture, not published)." if spec.get("fixture")
          else f"public/models/{probe}.glb and .webp, baselines/{probe}.png and the site's model credits updated."))

def cmd_new(args):
    if not args or not re.fullmatch(r"[a-z0-9_]+", args[0]):
        die('usage: run.py new <probe> ["Title"]   (probe: lowercase letters, digits, _)')
    probe, title = args[0], (args[1] if len(args) > 1 else args[0].title())
    targets = {os.path.join(HERE, "specs", f"{probe}.json"): "spec.json",
               os.path.join(HERE, "probes", f"{probe}.py"): "probe.py"}
    for path in targets:
        if os.path.exists(path):
            die(f"{os.path.relpath(path, HERE)} already exists")
    for path, template in targets.items():
        text = open(os.path.join(HERE, "templates", template)).read()
        open(path, "w").write(text.replace("__PROBE__", probe).replace("__TITLE__", title))
        print(f"created {os.path.relpath(path, HERE)}")
    os.makedirs(os.path.join(HERE, "refs", probe), exist_ok=True)
    print(f"Put reference images in refs/{probe}/, fill in the spec, then: run.py build {probe}")

def cmd_ref(args):
    if len(args) != 2:
        die("usage: run.py ref <probe> <model.glb|.gltf|.obj|.fbx|.stl>")
    probe, model = args[0], os.path.abspath(args[1])
    if not os.path.exists(model):
        die(f"{model} not found")
    check_version()
    proc = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                           "--python", os.path.join(HERE, "ref.py"), "--", probe, model],
                          capture_output=True, text=True)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("REF_OK ")), None)
    if not line:
        die(proc.stdout[-4000:] + proc.stderr[-4000:])
    info = json.loads(line[7:])
    parts = os.path.join(OUT, probe, "ref", "parts.json")
    print(f"{info['model']}: {info['triangles']:,} tris, size {info['size_m']} m, {info['pieces']} pieces")
    print(f"  grid {info['grid_m']}")
    print(f"  sheet: {os.path.join(HERE, 'refs', probe, 'reference-sheet.png')}")
    print(f"  pieces (largest first): {parts}")
    for r in json.load(open(parts))["largest_pieces"][:12]:
        print(f"    {r['main_length']:>7} m  size {r['size']}  centre {r['centre']}  {r['material']}")

def cmd_explode(args):
    if len(args) != 2:
        die("usage: run.py explode <probe> <model.glb|.gltf|.obj|.fbx|.stl>  (after a build)")
    probe, model = args[0], os.path.abspath(args[1])
    if not os.path.exists(model):
        die(f"{model} not found")
    check_version()
    proc = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                           "--python", os.path.join(HERE, "explode.py"), "--", probe, model],
                          capture_output=True, text=True)
    if not any(l.startswith("EXPLODE_OK ") for l in proc.stdout.splitlines()):
        die(proc.stdout[-4000:] + proc.stderr[-4000:])
    out = os.path.join(OUT, probe, "ref")
    rep = json.load(open(os.path.join(out, "explode.json")))
    print(f"{rep['model']}: {rep['claimed']}/{rep['pieces']} pieces claimed by our parts")
    print(f"  {'part':<16}{'ref pieces':>11}  centre off (cm)   ref size / ours (m)")
    for fam, r in rep["families"].items():
        if r["ref"]:
            off = math.sqrt(sum(x * x for x in r["centre_offset"])) * 100
            print(f"  {fam:<16}{r['ref']['pieces']:>11}  {off:>15.0f}   {r['ref']['size']} / {r['ours']['size']}")
        else:
            print(f"  {fam:<16}{'none':>11}")
    print("  unclaimed groups (largest first):")
    for i, u in enumerate(rep["unclaimed"][:12]):
        print(f"    {i:>2}: {u['pieces']:>4} pieces  size {u['size']}  centre {u['centre']}  "
              f"{u['nearest_m'] * 100:.0f} cm from {u['nearest_part']}")
    print(f"  image: {os.path.join(out, 'explode.png')}")

def cmd_bake(args):
    if len(args) != 2:
        die("usage: run.py bake <probe> <reference model .glb>  (spec needs a \"bake\" section)")
    probe, model = args[0], os.path.abspath(args[1])
    if not os.path.exists(model):
        die(f"{model} not found")
    check_version()
    proc = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                           "--python", os.path.join(HERE, "bake.py"), "--", probe, model],
                          capture_output=True, text=True)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("BAKE_OK ")), None)
    if not line:
        die(proc.stdout[-4000:] + proc.stderr[-4000:])
    info = json.loads(line[8:])
    print(f"baked {info['parts']} parts from {info['reference']} (frame {info['frame']}), by pass {info.get('coverage_by_pass')}: "
          f"{info['coverage']:.0%} of the atlas from the reference, the rest our own colours")
    print(f"  atlas {info['size']} px, {info['atlas_used']:.0%} used; {info['hidden_faces']} of {info['faces']} faces hidden"
          + (f"; normal map {info['normal_size']} px" if info.get("normal_size") else ""))
    print(f"  atlas: {os.path.join(HERE, 'refs', probe, 'baked.jpg')}")
    print(f"  projection only: {os.path.join(OUT, probe, 'bake_projection.png')}")
    print(f"  now rebuild: run.py build {probe}")

def _tool(script, args, ok=None):
    """Run a tools/ Blender script headless and pass its output through."""
    check_version()
    proc = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                           "--python", os.path.join(HERE, "tools", script), "--", *args],
                          capture_output=True, text=True)
    lines = [l for l in proc.stdout.splitlines()
             if re.match(r"(PIECE|STRUT|COUNT|ID|IDVIEW_OK|COMPARE_OK|\S+ +v *\d+ )", l)]
    if proc.returncode or (ok and not any(l.startswith(ok) for l in lines)):
        die(proc.stdout[-4000:] + proc.stderr[-4000:])
    print("\n".join(lines))

def _model_arg(path):
    path = os.path.abspath(path)
    if not os.path.exists(path):
        die(f"{path} not found")
    return path

def cmd_pieces(args):
    if len(args) < 7:
        die("usage: run.py pieces <model> x0 y0 z0 x1 y1 z1 [--min M] [--max M] [--struts] [--dump]")
    _tool("pieces.py", [_model_arg(args[0]), *args[1:]], ok="COUNT")

def cmd_idview(args):
    if len(args) != 14:
        die("usage: run.py idview <model> <out.png> x0 y0 z0 x1 y1 z1 tx ty tz dx dy dz")
    _tool("idview.py", [_model_arg(args[0]), os.path.abspath(args[1]), *args[2:]], ok="IDVIEW_OK")

def cmd_compare(args):
    if len(args) < 4:
        die("usage: run.py compare <probe> <reference> <out.png> tx,ty,tz,dx,dy,dz [...]  (after a build)")
    ours = os.path.join(OUT, args[0], f"{args[0]}.glb")
    if not os.path.exists(ours):
        die(f"{ours} not found: run.py build {args[0]} first")
    _tool("compare.py", [_model_arg(args[1]), ours, os.path.abspath(args[2]), *args[3:]], ok="COMPARE_OK")

# --- photos of the real vehicle -----------------------------------------------------------

def _photo_paths(probe, name=None):
    dl = os.path.join(OUT, probe, "photos")        # downloads (data, never run)
    keep = os.path.join(HERE, "refs", probe, "photos")  # fit settings and cameras (in git)
    os.makedirs(dl, exist_ok=True)
    os.makedirs(keep, exist_ok=True)
    if name is None:
        return dl, keep
    jpg = os.path.join(dl, f"{name}.jpg")
    return jpg, os.path.join(keep, f"{name}.fit.json"), os.path.join(keep, f"{name}.camera.json"), dl

def _photo_blender(probe, mode, *rest):
    blend = os.path.join(OUT, probe, f"{probe}.blend")
    if not os.path.exists(blend):
        die(f"{blend} not found: run.py build {probe} first")
    check_version()
    proc = subprocess.run([BLENDER, "--background", blend, "--python-exit-code", "1",
                           "--python", os.path.join(HERE, "tools", "photo_blender.py"), "--", mode, *rest],
                          capture_output=True, text=True)
    lines = [l for l in proc.stdout.splitlines() if l.startswith(("CAST", "PHOTO_OK"))]
    if proc.returncode or not any(l.startswith("PHOTO_OK") for l in lines):
        die(proc.stdout[-4000:] + proc.stderr[-4000:])
    return lines

def cmd_photo(args):
    usage = "usage: run.py photo get|fit|view|trace|cast <probe> ... (see run.py's header)"
    if len(args) < 3:
        die(usage)
    sub, probe = args[0], args[1]
    if sub == "get":
        import urllib.request
        dl, keep = _photo_paths(probe)
        index_p = os.path.join(keep, "photos.json")
        index = json.load(open(index_p)) if os.path.exists(index_p) else {}
        for a in args[2:]:
            if a.startswith("http"):
                url, name = a, os.path.splitext(os.path.basename(a.split("?")[0]))[0]
            else:  # a Smithsonian image id: ask for more than it has, it sends its largest
                url, name = f"https://ids.si.edu/ids/deliveryService?id={a}&max=8000", a
            path = os.path.join(dl, f"{name}.jpg")
            urllib.request.urlretrieve(url, path)
            with open(path, "rb") as fh:
                if fh.read(3) != b"\xff\xd8\xff":
                    os.remove(path)
                    die(f"{a}: not a JPEG (wrong id or url?)")
            index[name] = url
            print(f"  {name}  {os.path.getsize(path) // 1024} KB  {path}")
        json.dump(index, open(index_p, "w"), indent=1, sort_keys=True)
        return
    if len(args) < 3:
        die(usage)
    name = args[2]
    jpg, fit_p, cam_p, dl = _photo_paths(probe, name)
    if not os.path.exists(jpg):
        die(f"{jpg} not found: run.py photo get {probe} <id or url>")
    if sub == "fit":
        if not os.path.exists(fit_p):
            die(f"write {fit_p} first: landmarks (see tools/photo_fit.py)")
        npz = os.path.join(dl, "model.npz")
        _photo_blender(probe, "export", npz)
        overlay = os.path.join(dl, f"{name}-overlay.png")
        proc = subprocess.run([sys.executable, "-I", os.path.join(HERE, "tools", "photo_fit.py"), npz, jpg, fit_p, cam_p, overlay],
                              capture_output=True, text=True)
        print(proc.stdout.strip())
        if proc.returncode:
            die(proc.stderr[-4000:])
        print(f"  overlay: {overlay}\n  now: run.py photo view {probe} {name}")
    elif sub == "view":
        if not os.path.exists(cam_p):
            die(f"{cam_p} not found: run.py photo fit {probe} {name}")
        render = os.path.join(dl, f"{name}-model.png")
        _photo_blender(probe, "render", cam_p, render)
        from PIL import Image
        a, b = Image.open(jpg).convert("RGB"), Image.open(render).convert("RGB")
        side = Image.new("RGB", (a.width * 2, a.height))
        side.paste(a, (0, 0))
        side.paste(b.resize(a.size), (a.width, 0))
        side.thumbnail((3000, 3000))
        out = os.path.join(dl, f"{name}-view.jpg")
        side.save(out, quality=88)
        print(f"  photo | model: {out}")
    elif sub == "trace":
        if len(args) < 5:
            die("usage: run.py photo trace <probe> <photo> <frame.json> <out.png> [px_per_m]")
        for l in _photo_blender(probe, "trace", jpg, cam_p, os.path.abspath(args[3]), os.path.abspath(args[4]),
                                args[5] if len(args) > 5 else "400"):
            print(" ", l)
    elif sub == "cast":
        for l in _photo_blender(probe, "cast", cam_p, *args[3:]):
            print(" ", l)
    else:
        die(usage)

def cmd_dev(args):
    names = [a for a in args if not a.startswith("--")]
    headless = "--headless" in args
    watched = lambda: {p: os.path.getmtime(p) for d in ("probes", "specs", "lib")
                       for p in glob.glob(os.path.join(HERE, d, "*.py" if d != "specs" else "*.json"))}
    target = names[0] if names else None
    if target and target not in probes():
        die(f"No spec for '{target}'. Known: {', '.join(probes())}")
    sys.stdout.reconfigure(line_buffering=True)
    where = "the live session" if not headless and live_here() else "headless Blender"
    print(f"Rebuilding {target or 'the probe you save'} on every save, in {where} (Ctrl+C to stop)...")
    seen = watched()
    if target:  # build once now, so a save made while starting up isn't missed
        try:
            build(target, headless=headless)
        except SystemExit:
            pass
    while True:
        time.sleep(0.3)
        now = watched()
        changed = [p for p, t in now.items() if seen.get(p) != t]
        seen = now
        if not changed:
            continue
        time.sleep(0.2)  # let an editor finish writing
        seen = watched()
        own = {os.path.splitext(os.path.basename(p))[0] for p in changed if not p.startswith(os.path.join(HERE, "lib"))}
        if target:
            todo = [target]  # lib/ changes and the target's own files both rebuild it
        elif own:
            todo = sorted(own & set(probes()))
        else:  # lib/ changed: rebuild whatever was built last
            last = (read_status().get("current") or {}).get("probe")
            todo = [last] if last in probes() else []
        print(f"\n{time.strftime('%H:%M:%S')}  changed: {', '.join(os.path.relpath(p, HERE) for p in changed)}")
        for probe in todo:
            try:
                build(probe, headless=headless)
            except SystemExit:
                pass  # build() already printed why; keep watching

def cmd_status(args):
    status = read_status()
    cur = status.get("current")
    if cur:
        print(f"last step: {cur['probe']} {cur['step']} ({cur['state']}) {cur.get('message') or ''}")
    sys.path.insert(0, HERE)
    from lib import published
    for p, entry in sorted(status.get("probes", {}).items()):
        print_entry(p, entry)
        changed = published.behind(p)
        if changed is None:
            continue
        mine = [c for c in changed if published.own(p, c)]
        shared = [c for c in changed if not published.own(p, c)]
        if not changed:
            print("  ✓ published version is current")
        if mine:
            print(f"  ✗ published version is behind: {', '.join(mine)} changed since approve")
        if shared:
            print(f"  ! shared harness code changed since approve ({', '.join(shared)}): rebuild to see if it differs")

def cmd_watch(args):
    imgcat = shutil.which("imgcat") or "/Applications/iTerm.app/Contents/Resources/utilities/imgcat"
    if not os.path.exists(imgcat):
        die("imgcat not found (it ships with iTerm2)")
    sys.stdout.reconfigure(line_buffering=True)  # keep text and images in order
    print("Watching for new contact sheets (Ctrl+C to stop)...")
    seen = {p: e.get("started") for p, e in read_status().get("probes", {}).items()}
    last_step = None
    while True:
        status = read_status()
        cur = status.get("current")
        if cur and (cur["probe"], cur["step"], cur.get("at")) != last_step:
            last_step = (cur["probe"], cur["step"], cur.get("at"))
            print(f"{time.strftime('%H:%M:%S')}  {cur['probe']}: {cur['step']} {cur.get('message') or ''}")
        for p, entry in status.get("probes", {}).items():
            if entry.get("started") != seen.get(p) and cur and cur["state"] != "running":
                seen[p] = entry.get("started")
                if entry.get("sheet") and os.path.exists(entry["sheet"]):
                    subprocess.run([imgcat, entry["sheet"]])
                print_entry(p, entry)
        time.sleep(0.5)

COMMANDS = {"blender": cmd_blender, "build": cmd_build, "all": cmd_all, "approve": cmd_approve,
            "new": cmd_new, "ref": cmd_ref, "explode": cmd_explode, "bake": cmd_bake, "pieces": cmd_pieces, "idview": cmd_idview,
            "compare": cmd_compare, "photo": cmd_photo, "dev": cmd_dev, "send": cmd_send, "status": cmd_status, "watch": cmd_watch}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        die("".join(l[2:] for l in open(__file__) if l.startswith(("#   run.py", "#          ", "#            "))))
    try:
        COMMANDS[sys.argv[1]](sys.argv[2:])
    except KeyboardInterrupt:
        pass
