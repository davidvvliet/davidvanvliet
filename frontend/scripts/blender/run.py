#!/usr/bin/env python3
# Command line for the probe-modelling harness (plain Python 3, no dependencies).
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
#   run.py dev [probe] [--headless] rebuild on every save of a probe script, spec or lib/
#   run.py send <file.py | ->       run Python in the live session
#   run.py status                   print the last build of every probe
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
    if not headless and live_available():
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

def cmd_dev(args):
    names = [a for a in args if not a.startswith("--")]
    headless = "--headless" in args
    watched = lambda: {p: os.path.getmtime(p) for d in ("probes", "specs", "lib")
                       for p in glob.glob(os.path.join(HERE, d, "*.py" if d != "specs" else "*.json"))}
    target = names[0] if names else None
    if target and target not in probes():
        die(f"No spec for '{target}'. Known: {', '.join(probes())}")
    sys.stdout.reconfigure(line_buffering=True)
    where = "the live session" if not headless and live_available() else "headless Blender"
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
    for p, entry in sorted(status.get("probes", {}).items()):
        print_entry(p, entry)

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
            "new": cmd_new, "ref": cmd_ref, "explode": cmd_explode, "dev": cmd_dev, "send": cmd_send, "status": cmd_status, "watch": cmd_watch}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        die("".join(l[2:] for l in open(__file__) if l.startswith(("#   run.py", "#          ", "#            "))))
    try:
        COMMANDS[sys.argv[1]](sys.argv[2:])
    except KeyboardInterrupt:
        pass
