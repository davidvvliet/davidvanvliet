# A recipe (boards/<board>/recipe.json) as a KiCad board: every block's parts placed, wired and with its
# own traces, the blocks' ports joined as the recipe says, and the board outline. Routing is lib/route.py.
# Runs in KiCad's Python:
#   <kicad-python> lib/generate.py <recipe.json> <out dir>    -> board.kicad_pcb, .kicad_pro, .kicad_sch, blocks.json
import json, os, re, shutil, sys
import pcbnew

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS)
from lib import schematic
BOARD = os.path.basename(os.path.dirname(os.path.abspath(recipe_path := sys.argv[1])))
out = sys.argv[2]
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
def local(inst, n):
    """The board's name for a block's net: joined ports' shared name, else "core:XIN" (no "/", which a schematic label can't hold)."""
    return alias.get((inst, n), f"{inst}:{n.lstrip('/')}")
nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); nets[name] = n
    return nets[name]

refs_used, block_of, sch_parts = set(), {}, []
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
            if len(pins) == 1 and (inst, n) not in alias:  # a pin on its own: no-connect in the schematic, named as KiCad names it
                part = next(q for q in blk["parts"] if q["ref"] == ref)
                name = schematic.symbols.pin_names(schematic.symbols.get(part["symbol"])).get(pad, "")
                pad_net[(ref, pad)] = f"unconnected-({rename[ref]}{'-' + name.replace('/', '{slash}') if name and name != '~' else ''}-Pad{pad})"
            else:
                pad_net[(ref, pad)] = local(inst, n)
    for p in blk["parts"]:
        f = footprint(p["footprint"])
        pl = blk["layout"]["place"][p["ref"]]
        board.Add(f)
        if pl["side"] == "back":
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetOrientationDegrees(pl["rotation"])
        f.SetPosition(pcbnew.VECTOR2I(mm(ox + pl["at_mm"][0]), mm(oy + pl["at_mm"][1])))
        f.SetReference(rename[p["ref"]]); f.SetValue(p["value"])
        pin_net, names = {}, schematic.symbols.pin_names(schematic.symbols.get(p["symbol"]))
        for pad in f.Pads():
            n = pad_net.get((p["ref"], pad.GetNumber()))
            if not n and pad.GetNumber() in names:  # a pin the block leaves open: no-connect, named as KiCad names it
                name = names[pad.GetNumber()]
                n = f"unconnected-({rename[p['ref']]}{'-' + name.replace('/', '{slash}') if name and name != '~' else ''}-Pad{pad.GetNumber()})"
            if n: pad.SetNet(net(n)); pin_net[pad.GetNumber()] = n
        block_of[rename[p["ref"]]] = blk["title"] or spec["block"]
        # The footprint points at its symbol in the schematic (KiCad's schematic-to-board comparison).
        sym = schematic.uid(BOARD, "symbol", rename[p["ref"]])
        f.SetPath(pcbnew.KIID_PATH("/" + sym)); f.SetSheetname("/"); f.SetSheetfile("board.kicad_sch")
        sch_parts.append({"ref": rename[p["ref"]], "value": p["value"], "footprint": p["footprint"], "symbol": p["symbol"],
                          "uuid": sym, "block": block_of[rename[p["ref"]]], "nets": pin_net,
                          "datasheet": f.GetField(pcbnew.FIELD_T_DATASHEET).GetText(),
                          "pin_types": p.get("pin_types", {}),
                          "in_bom": not f.IsExcludedFromBOM()})  # mounting holes and test points: as their footprints say
    for t in blk["layout"]["traces"]:
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I(mm(ox + t["from_mm"][0]), mm(oy + t["from_mm"][1])))
        tr.SetEnd(pcbnew.VECTOR2I(mm(ox + t["to_mm"][0]), mm(oy + t["to_mm"][1])))
        tr.SetWidth(mm(t["width_mm"])); tr.SetLayer(board.GetLayerID(t["layer"]))
        tr.SetNet(net(local(inst, t["net"]))); board.Add(tr)
    for v in blk["layout"]["vias"]:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pcbnew.VECTOR2I(mm(ox + v["at_mm"][0]), mm(oy + v["at_mm"][1])))
        via.SetDrill(mm(v["drill_mm"])); via.SetWidth(mm(v["size_mm"]))
        via.SetNet(net(local(inst, v["net"]))); board.Add(via)

# Outline: a rectangle on Edge.Cuts, its corners rounded by the recipe's "corner_radius_mm" (none: square).
w, h = recipe["board"]["size_mm"]
r = recipe["board"].get("corner_radius_mm", 0)
k = r * (1 - 0.5 ** 0.5)  # an arc's midpoint lies this far in from its corner on both axes
def edge(*pts):
    s = pcbnew.PCB_SHAPE(board); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.05))
    v = [pcbnew.VECTOR2I(mm(x), mm(y)) for x, y in pts]
    if len(v) == 3: s.SetShape(pcbnew.SHAPE_T_ARC); s.SetArcGeometry(*v)
    else: s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(v[0]); s.SetEnd(v[1])
    board.Add(s)
for side, arc in [(((r, 0), (w - r, 0)), ((w - r, 0), (w - k, k), (w, r))),
                  (((w, r), (w, h - r)), ((w, h - r), (w - k, h - k), (w - r, h))),
                  (((w - r, h), (r, h)), ((r, h), (k, h - k), (0, h - r))),
                  (((0, h - r), (0, r)), ((0, r), (k, k), (r, 0)))]:
    edge(*side)
    if r: edge(*arc)

pcb_file = os.path.join(out, "board.kicad_pcb")
pcbnew.SaveBoard(pcb_file, board)

# Colours: the recipe's "mask" (solder mask, the board's colour; the traces show through it) and "silk"
# (the printing), as KiCad colour names ("Black") or "#RRGGBB[AA]". KiCad's 3D export reads them from the
# board's stackup, written here as the Mitayi's file has it (pcbnew's stackup calls abort outside the editor).
# Without "mask", KiCad's default green.
if recipe["board"].get("mask"):
    text = open(pcb_file).read()
    total = float(re.search(r"\(thickness ([\d.]+)\)", text).group(1))
    mask, silk = recipe["board"]["mask"], recipe["board"].get("silk", "White")
    def layer(name, kind, *extra): return f'(layer "{name}" (type "{kind}") {" ".join(extra)})'
    stackup = " ".join([
        "(stackup",
        layer("F.SilkS", "Top Silk Screen", f'(color "{silk}")'), layer("F.Paste", "Top Solder Paste"),
        layer("F.Mask", "Top Solder Mask", f'(color "{mask}")', "(thickness 0.01)"),
        layer("F.Cu", "copper", "(thickness 0.035)"),
        layer("dielectric 1", "core", '(color "FR4 natural")', f"(thickness {total - 0.09:g})", '(material "FR4")', "(epsilon_r 4.5)", "(loss_tangent 0.02)"),
        layer("B.Cu", "copper", "(thickness 0.035)"),
        layer("B.Mask", "Bottom Solder Mask", f'(color "{mask}")', "(thickness 0.01)"),
        layer("B.Paste", "Bottom Solder Paste"), layer("B.SilkS", "Bottom Silk Screen", f'(color "{silk}")'),
        *([f'(copper_finish "{recipe["board"]["finish"]}")'] if recipe["board"].get("finish") else []),
        "(dielectric_constraints no))"])
    assert "(stackup" not in text
    open(pcb_file, "w").write(text.replace("(setup", "(setup " + stackup, 1))
schematic.write(os.path.join(out, "board.kicad_sch"), BOARD, sch_parts, recipe["title"])
json.dump(block_of, open(os.path.join(out, "blocks.json"), "w"), indent=1)
print("GENERATED", len(block_of), "parts", len(nets), "nets", flush=True)
