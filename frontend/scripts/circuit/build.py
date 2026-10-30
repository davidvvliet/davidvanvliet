# Build a board for /circuits (from frontend/; boards/<board>/ holds its KiCad files):
#   python3 scripts/circuit/build.py <board>            out/<board>/<board>.glb and .json, shown on /models?dashboard
#   python3 scripts/circuit/build.py <board> --publish  the same, then copied to public/circuits/ (the live /circuits page)
# A board is either imported (board.json + someone's KiCad files) or ours (recipe.json + blocks/):
# 0. Ours: lib/generate.py lays the blocks out as KiCad's board, lib/route.py and Freerouting route it.
# 1. KiCad's checks (lib/checks.py): design rules on the board, electrical rules on the schematic.
# 2. KiCad (kicad-cli) exports the layout in 3D, with its library's part models.
# 3. Blender (lib/pack.py) tags every part with the schematic section it is drawn in (lib/sections.py),
#    merges each block's pieces into one mesh per material and writes the web model.
# See README.md.
import json, os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import checks, tools
from lib.sections import sections as find_sections
FRONTEND = tools.FRONTEND

def nice(title):
    """A schematic section title as a block name: "FLASH MEMORY" -> "Flash memory", acronyms kept."""
    words = title.split()
    out = [w if not w.isalpha() or w in ("LDO", "LED", "SWD") else w.lower() for w in words]
    return " ".join(out)[:1].upper() + " ".join(out)[1:]

ROUTE_TRIES = 8
ROUTE_MARGIN_UM = 25  # extra clearance for the router (see README: "Routing")

def kpy(*args):
    """Run a lib/ script in KiCad's Python; its lines starting with an upper-case tag."""
    r = subprocess.run([tools.tool("kicad-python"), "-I", "-u", *args], capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if re.match(r"^[A-Z]+ ", l)]
    if r.returncode or not lines:
        sys.exit(f"{os.path.basename(args[0])} failed:\n" + "\n".join(l for l in (r.stdout + r.stderr).splitlines()
                                                                      if not re.search(r"swig/python|Fontconfig|assert", l))[-3000:])
    return lines

def route(work, ground):
    """Route work/board.kicad_pcb, trying again (the router varies between runs) until KiCad's design
    rule check finds no error and nothing unconnected; keeps the best try. Returns its report."""
    best = None
    for i in range(ROUTE_TRIES):
        t = os.path.join(work, f"try{i}"); os.makedirs(t, exist_ok=True)
        for ext in ("kicad_pcb", "kicad_pro"): shutil.copy(os.path.join(work, f"unrouted.{ext}"), os.path.join(t, f"board.{ext}"))
        pcb, dsn, ses = (os.path.join(t, f) for f in ("board.kicad_pcb", "board.dsn", "board.ses"))
        kpy(os.path.join(HERE, "lib", "route.py"), "export", pcb, dsn)
        text = open(dsn).read()
        text = re.sub(r"\(clearance (\d+(?:\.\d+)?)\)", lambda m: f"(clearance {float(m.group(1)) + ROUTE_MARGIN_UM:g})", text)
        open(dsn, "w").write(text)
        # Headless, and no Dock icon (apple.awt.UIElement): otherwise macOS gives Java focus and switches Spaces.
        r = subprocess.run([tools.tool("java"), "-Djava.awt.headless=true", "-Dapple.awt.UIElement=true", "-jar", tools.tool("freerouting"), "--gui.enabled=false",
                            "--usage_and_diagnostic_data.disable_analytics=true", "--router.autorouter.max_passes=100",
                            "-de", dsn, "-do", ses], capture_output=True, text=True)
        if not os.path.exists(ses):
            sys.exit("Freerouting failed:\n" + (r.stdout + r.stderr)[-2000:])
        kpy(os.path.join(HERE, "lib", "route.py"), "import", pcb, ses, ground or "")
        rows = checks.drc(pcb, parity=False)
        bad = sum(c["measured"] for c in rows if not c["ok"])
        if best is None or bad < best[0]: best = (bad, pcb, i + 1)
        if bad == 0: break
    shutil.copy(best[1], os.path.join(work, "board.kicad_pcb"))
    shutil.copy(os.path.join(work, "unrouted.kicad_pro"), os.path.join(work, "board.kicad_pro"))
    return f"routed in {best[2]} of {ROUTE_TRIES} tries" + ("" if best[0] == 0 else f", best has {best[0]} problems")

def main(board, publish=False):
    started = time.time()
    src = os.path.join(HERE, "boards", board)
    work = os.path.join(HERE, "out", board, "kicad")  # the generated board, kept for opening in KiCad
    note = None
    if os.path.exists(os.path.join(src, "recipe.json")):
        recipe = json.load(open(os.path.join(src, "recipe.json")))
        shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
        kpy(os.path.join(HERE, "lib", "generate.py"), os.path.join(src, "recipe.json"), work)
        for ext in ("kicad_pcb", "kicad_pro"): os.rename(os.path.join(work, f"board.{ext}"), os.path.join(work, f"unrouted.{ext}"))
        note = route(work, recipe["board"].get("ground_fill"))
        meta = {"title": recipe["title"], "purpose": recipe["purpose"], "source": recipe["source"], "pcb": "kicad/board.kicad_pcb", "sch": "kicad/board.kicad_sch"}
        pcb_path, sch_path = os.path.join(work, "board.kicad_pcb"), os.path.join(work, "board.kicad_sch")
        blocks = json.load(open(os.path.join(work, "blocks.json")))
    else:
        meta = json.load(open(os.path.join(src, "board.json")))
        pcb_path, sch_path = os.path.join(src, meta["pcb"]), os.path.join(src, meta["sch"])
        blocks = {ref: nice(s) for ref, s in find_sections(sch_path).items() if s}
    pcb = open(pcb_path).read()
    # Older projects name the model folder by KiCad version, and KiCad 10 ships STEP models only.
    pcb = re.sub(r"\$\{(KICAD\d*_3DMODEL_DIR|KISYS3DMOD)\}", "${KICAD10_3DMODEL_DIR}", pcb)
    pcb = re.sub(r'(\(model "(?!\$\{CIRCUIT_3DMODELS\})[^"]+)\.wrl"', r'\1.step"', pcb)
    # Our own 3D models (footprints/models/: datasheet-sized boxes for parts KiCad has no model of).
    pcb = pcb.replace("${CIRCUIT_3DMODELS}", os.path.join(HERE, "footprints", "models"))
    for a, b in meta.get("model_renames", {}).items():
        pcb = pcb.replace(a, b)
    with tempfile.TemporaryDirectory() as tmp:
        # One project: the checks need its rules (.kicad_pro) and schematic beside the board, all named alike.
        p = os.path.join(tmp, "board.kicad_pcb"); open(p, "w").write(pcb)
        pro = os.path.splitext(pcb_path)[0] + ".kicad_pro"
        if os.path.exists(pro): shutil.copy(pro, os.path.join(tmp, "board.kicad_pro"))
        if sch_path:
            shutil.copy(sch_path, os.path.join(tmp, "board.kicad_sch"))
            kicad_checks = checks.drc(p) + checks.erc(os.path.join(tmp, "board.kicad_sch"))
        else:
            kicad_checks = checks.drc(p, parity=False)
        raw = os.path.join(tmp, "raw.glb")
        r = subprocess.run([tools.tool("kicad-cli"), "pcb", "export", "glb", "-f", "-o", raw, "--no-dnp", "--include-tracks", "--include-pads",
                            "--include-zones", "--include-silkscreen", "--include-soldermask", p], capture_output=True, text=True)
        missing = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("Could not add 3D model")]
        if r.returncode or not os.path.exists(raw):
            sys.exit(r.stdout + r.stderr)
        tags = os.path.join(tmp, "blocks.json"); json.dump(blocks, open(tags, "w"))
        out = os.path.join(HERE, "out", board, f"{board}.glb")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        r = subprocess.run([tools.tool("blender"), "-b", "--factory-startup", "--python", os.path.join(HERE, "lib", "pack.py"), "--", raw, tags, out],
                           capture_output=True, text=True)
        stats = [l for l in r.stdout.splitlines() if l.startswith("PACK")]
        if r.returncode or not stats:
            record(board, {"started": started, "ok": False, "error": (r.stdout[-1500:] + r.stderr[-1500:])})
            sys.exit(r.stdout[-3000:] + r.stderr[-3000:])
        pack = json.loads(stats[-1][5:])
        placed = set(pack["placed"])
    # Parts per block, from the layout (value and footprint), for the blocks that have a 3D part.
    parts = {}
    for m in re.finditer(r'\(footprint "([^"]+)"(.*?)\n\t\)', pcb, re.S):
        ref = re.search(r'\(property "Reference" "([^"]+)"', m.group(2))
        val = re.search(r'\(property "Value" "([^"]+)"', m.group(2))
        if ref and ref.group(1) in placed and ref.group(1) in blocks:
            parts.setdefault(blocks[ref.group(1)], []).append(
                {"ref": ref.group(1), "value": val.group(1) if val else "", "package": m.group(1).split(":")[-1]})
    key = lambda p: (re.sub(r"\d", "", p["ref"]), int(re.sub(r"\D", "", p["ref"]) or 0))
    data = {"board": board, "title": meta["title"], "purpose": meta["purpose"], "source": meta["source"],
            "blocks": [{"name": n, "parts": sorted(ps, key=key)} for n, ps in sorted(parts.items(), key=lambda kv: -len(kv[1]))]}
    json.dump(data, open(os.path.join(HERE, "out", board, f"{board}.json"), "w"), indent=1)
    mb, tris = os.path.getsize(out) / 1e6, sum(pack["tris"].values())
    # The dashboard's check table (same shape as the Blender harness's checks).
    rows = kicad_checks + [{"name": "file size", "ok": mb <= 1.5, "measured": round(mb, 2), "expected": 1.5, "unit": "MB"},
              {"name": "triangles", "ok": tris <= 300000, "measured": tris, "expected": 300000, "unit": "tris"},
              {"name": "parts without a 3D model", "ok": not missing, "measured": len(missing), "expected": 0, "unit": "parts"}]
    record(board, {"started": started, "ok": all(c["ok"] for c in rows), "seconds": round(time.time() - started, 1),
                   "glb": f"{board}.glb", "checks": rows, "published": publish})
    if publish:  # the /circuits page lists every public/circuits/<name>.board.json
        dest = os.path.join(FRONTEND, "public", "circuits"); os.makedirs(dest, exist_ok=True)
        shutil.copy(out, os.path.join(dest, f"{board}.glb"))
        shutil.copy(os.path.join(HERE, "out", board, f"{board}.json"), os.path.join(dest, f"{board}.board.json"))
    for c in rows:
        print(f"  {'✓' if c['ok'] else '✗'} {c['name']}: {c['measured']} {c['unit']}" + (f"  ({c['detail']})" if c.get("detail") else ""))
    if note: print(f"  {note}")
    print(f"{board}: {'PASS' if all(c['ok'] for c in rows) else 'FAIL'}, {mb:.2f} MB, {tris} triangles, {len(data['blocks'])} blocks"
          + (f"; missing models: {missing}" if missing else "") + ("; published to public/circuits" if publish else ""))

def record(board, build):
    """out/status.json, which /api/models/status reads for the dashboard."""
    path = os.path.join(HERE, "out", "status.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try: status = json.load(open(path))
    except (OSError, ValueError): status = {}
    status.setdefault("boards", {})[board] = build
    json.dump(status, open(path, "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1], "--publish" in sys.argv[2:])
