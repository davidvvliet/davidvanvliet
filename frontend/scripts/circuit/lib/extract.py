# Lift a block out of an imported board: its parts, wiring, ports and layout, as a block file skeleton
# (templates/block.json). Sources and quotes are added by hand from the datasheets afterwards.
# Runs in KiCad's Python (it reads the board with pcbnew):
#   <kicad-python> lib/extract.py <board.kicad_pcb> <board.kicad_sch> <name> <ref,ref,...> > blocks/<name>.json
import json, os, re, sys
import pcbnew

pcb_path, sch_path, name, refs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
board = pcbnew.LoadBoard(pcb_path)
mm = pcbnew.ToMM
FOOTPRINTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))), "..", "..", "..", "SharedSupport", "footprints")
FOOTPRINTS = os.path.normpath(os.environ.get("KICAD_FOOTPRINTS", FOOTPRINTS))

def in_library(fpid):
    lib, _, fp = fpid.partition(":")
    return os.path.exists(os.path.join(FOOTPRINTS, f"{lib}.pretty", f"{fp}.kicad_mod"))

# Schematic symbols (library id) per reference.
sch = open(sch_path).read()
symbols = {}
for m in re.finditer(r'\n\t\(symbol\s*\(lib_id "([^"]+)"\)(.*?)\n\t\)', sch, re.S):
    r = re.search(r'\(property "Reference" "([^"]+)"', m.group(2))
    if r: symbols[r.group(1)] = m.group(1)

fps = {f.GetReference(): f for f in board.GetFootprints()}
mine = [fps[r] for r in refs if r in fps]
missing = [r for r in refs if r not in fps]
# Every pad's net, and where else on the board each net goes.
pads_of_net = {}
for f in board.GetFootprints():
    for p in f.Pads():
        if p.GetNetname():
            pads_of_net.setdefault(p.GetNetname(), set()).add(f.GetReference())
nets = {}
for f in mine:
    for p in f.Pads():
        n = p.GetNetname()
        if n and p.GetNumber():
            nets.setdefault(n, []).append(f"{f.GetReference()}.{p.GetNumber()}")
ports = {n: sorted(pads_of_net[n] - set(refs)) for n in nets if pads_of_net.get(n, set()) - set(refs)}

# Layout relative to the block's corner (the lowest x and y of its parts' pads), in mm. (A footprint's own
# bounding box measures its text, which needs KiCad's window system and aborts here.)
xs, ys = [], []
for f in mine:
    for p in f.Pads():
        b = p.GetBoundingBox()
        xs += [mm(b.GetLeft()), mm(b.GetRight())]; ys += [mm(b.GetTop()), mm(b.GetBottom())]
x0, y0 = min(xs), min(ys)
place = {f.GetReference(): {"at_mm": [round(mm(f.GetPosition().x) - x0, 3), round(mm(f.GetPosition().y) - y0, 3)],
                             "rotation": round(f.GetOrientationDegrees(), 1),
                             "side": "back" if f.IsFlipped() else "front"} for f in mine}
# Traces whose net stays inside the block: its own wiring, kept with it.
internal = {n for n in nets if n not in ports}
traces, vias = [], []
for t in board.GetTracks():
    if t.GetNetname() not in internal: continue
    if t.GetClass() == "PCB_VIA":
        vias.append({"net": t.GetNetname(), "at_mm": [round(mm(t.GetPosition().x) - x0, 3), round(mm(t.GetPosition().y) - y0, 3)],
                     "drill_mm": round(mm(t.GetDrill()), 3), "size_mm": round(mm(t.GetWidth(pcbnew.F_Cu)), 3)})
    elif t.GetClass() == "PCB_TRACK":
        s, e = t.GetStart(), t.GetEnd()
        traces.append({"net": t.GetNetname(), "layer": t.GetLayerName(), "width_mm": round(mm(t.GetWidth()), 4),
                       "from_mm": [round(mm(s.x) - x0, 3), round(mm(s.y) - y0, 3)], "to_mm": [round(mm(e.x) - x0, 3), round(mm(e.y) - y0, 3)]})

parts = []
for f in mine:
    fpid = f.GetFPIDAsString()
    parts.append({"ref": f.GetReference(), "value": f.GetValue(), "symbol": symbols.get(f.GetReference(), ""),
                  "footprint": fpid, "footprint_in_kicad_library": in_library(fpid),
                  "source": "", "quote": ""})
print(json.dumps({
    "name": name, "title": "", "purpose": "",
    "taken_from": {"board": os.path.basename(pcb_path), "refs": refs, "missing": missing},
    "sources": [], "parts": parts,
    "nets": {n: sorted(p) for n, p in sorted(nets.items())},
    "ports": {n: {"net": n, "kind": "", "elsewhere_on_board": o} for n, o in sorted(ports.items())},
    "layout": {"size_mm": [round(max(xs) - x0, 3), round(max(ys) - y0, 3)], "place": place,
               "traces": traces, "vias": vias, "rules": ""},
    "open_questions": [],
}, indent=1))
