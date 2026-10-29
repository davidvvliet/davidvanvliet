# Build a board for /circuit: public/circuit/<board>.glb and .json.
#   python3 scripts/circuit/build.py <board>      (from frontend/; boards/<board>/ holds its KiCad files)
# 1. KiCad (kicad-cli) exports the layout in 3D, with its library's part models.
# 2. Blender (pack.py) tags every part with the schematic section it is drawn in (sections.py),
#    merges each block's pieces into one mesh per material and writes the web model.
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(os.path.dirname(HERE))
KICAD = os.environ.get("KICAD_CLI", os.path.expanduser("~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"))
BLENDER = json.load(open(os.path.join(FRONTEND, "scripts", "blender", "blender.json")))["path"] \
    if os.path.exists(os.path.join(FRONTEND, "scripts", "blender", "blender.json")) else "/Applications/Blender.app/Contents/MacOS/Blender"

def nice(title):
    """A schematic section title as a block name: "FLASH MEMORY" -> "Flash memory", acronyms kept."""
    words = title.split()
    out = [w if not w.isalpha() or w in ("LDO", "LED", "SWD") else w.lower() for w in words]
    return " ".join(out)[:1].upper() + " ".join(out)[1:]

def main(board):
    src = os.path.join(HERE, "boards", board)
    meta = json.load(open(os.path.join(src, "board.json")))
    pcb = open(os.path.join(src, meta["pcb"])).read()
    # Older projects name the model folder by KiCad version, and KiCad 10 ships STEP models only.
    pcb = re.sub(r"\$\{(KICAD\d*_3DMODEL_DIR|KISYS3DMOD)\}", "${KICAD10_3DMODEL_DIR}", pcb)
    pcb = re.sub(r'(\(model "[^"]+)\.wrl"', r'\1.step"', pcb)
    for a, b in meta.get("model_renames", {}).items():
        pcb = pcb.replace(a, b)
    sections = json.loads(subprocess.run([sys.executable, os.path.join(HERE, "sections.py"), os.path.join(src, meta["sch"])],
                                         check=True, capture_output=True, text=True).stdout)
    blocks = {ref: nice(s) for ref, s in sections.items() if s}
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "board.kicad_pcb"); open(p, "w").write(pcb)
        raw = os.path.join(tmp, "raw.glb")
        r = subprocess.run([KICAD, "pcb", "export", "glb", "-f", "-o", raw, "--no-dnp", "--include-tracks", "--include-pads",
                            "--include-zones", "--include-silkscreen", "--include-soldermask", p], capture_output=True, text=True)
        missing = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("Could not add 3D model")]
        if r.returncode or not os.path.exists(raw):
            sys.exit(r.stdout + r.stderr)
        tags = os.path.join(tmp, "blocks.json"); json.dump(blocks, open(tags, "w"))
        out = os.path.join(FRONTEND, "public", "circuit", f"{board}.glb")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python", os.path.join(HERE, "pack.py"), "--", raw, tags, out],
                           capture_output=True, text=True)
        stats = [l for l in r.stdout.splitlines() if l.startswith("PACK")]
        if r.returncode or not stats:
            sys.exit(r.stdout[-3000:] + r.stderr[-3000:])
        placed = set(json.loads(stats[-1][5:])["placed"])
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
    json.dump(data, open(os.path.join(FRONTEND, "public", "circuit", f"{board}.json"), "w"), indent=1)
    print(stats[-1][5:][:300])
    print(f"{board}: {os.path.getsize(out) / 1e6:.2f} MB, {len(data['blocks'])} blocks" + (f"; missing models: {missing}" if missing else ""))

if __name__ == "__main__":
    main(sys.argv[1])
