# A recipe (boards/<board>/recipe.json) as a KiCad board: every block's parts placed, wired and with its
# own traces, the blocks' ports joined as the recipe says, and the board outline. Routing is lib/route.py.
# Runs in KiCad's Python:
#   <kicad-python> lib/generate.py <recipe.json> <out dir>    -> board.kicad_pcb, board.kicad_pro, blocks.json
import json, os, re, shutil, sys
import pcbnew

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
recipe_path, out = sys.argv[1], sys.argv[2]
recipe = json.load(open(recipe_path))
KICAD_FP = os.path.normpath(os.path.join(os.path.dirname(sys.executable), *[".."] * 5, "SharedSupport", "footprints"))
KICAD_FP = os.environ.get("KICAD_FOOTPRINTS", KICAD_FP)
io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
mm = pcbnew.FromMM

def footprint(fpid):
    lib, _, name = fpid.partition(":")
    for root in (os.path.join(HARNESS, "footprints"), KICAD_FP):
        path = os.path.join(root, f"{lib}.pretty")
        if os.path.exists(os.path.join(path, f"{name}.kicad_mod")):
            f = io.FootprintLoad(path, name)
            f.SetFPID(pcbnew.LIB_ID(lib, name))
            return f
    sys.exit(f"footprint {fpid} not found in footprints/ or KiCad's library")

board = pcbnew.BOARD()
# Rules: the recipe's project file (clearances, widths, vias), copied beside the board.
shutil.copy(os.path.join(HARNESS, recipe["board"]["rules"]), os.path.join(out, "board.kicad_pro"))

# Nets: each block's own nets are its instance's ("core:/QSPI_SS"); joined ports share one net, named
# after the first port's net ("/VSYS" -> "VSYS").
alias = {}
for group in recipe["connect"]:
    name = group[0].split(".", 1)[1].lstrip("/")
    for port in group:
        inst, net = port.split(".", 1)
        alias[(inst, net)] = name
nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); nets[name] = n
    return nets[name]

refs_used, block_of = set(), {}
for inst, spec in recipe["blocks"].items():
    blk = json.load(open(os.path.join(HARNESS, "blocks", f"{spec['block']}.json")))
    ox, oy = spec["at_mm"]
    # References stay as in the block unless another block took them first: then the next free number.
    rename = {}
    for p in blk["parts"]:
        r = p["ref"]
        if r in refs_used:
            letters = re.sub(r"\d+$", "", r); i = 1
            while f"{letters}{i}" in refs_used: i += 1
            r = f"{letters}{i}"
        refs_used.add(r); rename[p["ref"]] = r
    pad_net = {}
    for n, pins in blk["nets"].items():
        for pin in pins:
            ref, pad = pin.split(".", 1)
            pad_net[(ref, pad)] = alias.get((inst, n), f"{inst}:{n}")
    for p in blk["parts"]:
        f = footprint(p["footprint"])
        pl = blk["layout"]["place"][p["ref"]]
        board.Add(f)
        if pl["side"] == "back":
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetOrientationDegrees(pl["rotation"])
        f.SetPosition(pcbnew.VECTOR2I(mm(ox + pl["at_mm"][0]), mm(oy + pl["at_mm"][1])))
        f.SetReference(rename[p["ref"]]); f.SetValue(p["value"])
        for pad in f.Pads():
            n = pad_net.get((p["ref"], pad.GetNumber()))
            if n: pad.SetNet(net(n))
        block_of[rename[p["ref"]]] = blk["title"] or spec["block"]
    for t in blk["layout"]["traces"]:
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I(mm(ox + t["from_mm"][0]), mm(oy + t["from_mm"][1])))
        tr.SetEnd(pcbnew.VECTOR2I(mm(ox + t["to_mm"][0]), mm(oy + t["to_mm"][1])))
        tr.SetWidth(mm(t["width_mm"])); tr.SetLayer(board.GetLayerID(t["layer"]))
        tr.SetNet(net(alias.get((inst, t["net"]), f"{inst}:{t['net']}"))); board.Add(tr)
    for v in blk["layout"]["vias"]:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pcbnew.VECTOR2I(mm(ox + v["at_mm"][0]), mm(oy + v["at_mm"][1])))
        via.SetDrill(mm(v["drill_mm"])); via.SetWidth(mm(v["size_mm"]))
        via.SetNet(net(alias.get((inst, v["net"]), f"{inst}:{v['net']}"))); board.Add(via)

# Outline: a rectangle on Edge.Cuts.
w, h = recipe["board"]["size_mm"]
corners = [(0, 0), (w, 0), (w, h), (0, h)]
for a, b in zip(corners, corners[1:] + corners[:1]):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.05))
    s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1]))); board.Add(s)

pcbnew.SaveBoard(os.path.join(out, "board.kicad_pcb"), board)
json.dump(block_of, open(os.path.join(out, "blocks.json"), "w"), indent=1)
print("GENERATED", len(block_of), "parts", len(nets), "nets", flush=True)
