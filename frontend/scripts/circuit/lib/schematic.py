# The schematic of a recipe board: each block a titled box (as designers draw them, and as
# lib/sections.py reads them), its symbols in rows, every pin tied to its net by a label at its tip
# (pins with the same label are connected), unused pins marked no-connect, and a power flag on each
# power net no pin drives (for KiCad's electrical check). Plain Python; generate.py calls write().
import math, uuid
from . import sexpr, symbols
Q = sexpr.Q
NS = uuid.UUID("6f1c2e1e-7d3c-4c1f-9d7e-3b0c1a5e2f10")
GRID = 2.54
PAPER = [("A4", (297, 210)), ("A3", (420, 297)), ("A2", (594, 420)), ("A1", (841, 594)), ("A0", (1189, 841))]  # landscape, mm

def uid(*key):
    """A UUID that stays the same between builds, so the board's footprints keep pointing at their symbols."""
    return str(uuid.uuid5(NS, "/".join(key)))

def snap(v): return round(round(v / GRID) * GRID, 4)

def _font(size=1.27, hide=False, justify=None):
    e = ["effects", ["font", ["size", size, size]]]
    if justify: e.append(["justify", *justify])
    if hide: e.append(["hide", "yes"])
    return e

def _prop(name, value, x, y, hide=False):
    return ["property", Q(name), Q(value), ["at", x, y, 0], _font(hide=hide)]

def _symbol(lib_id, ref, value, footprint, x, y, sym_uuid, root, pins, on_board=True, datasheet=""):
    return ["symbol", ["lib_id", Q(lib_id)], ["at", x, y, 0], ["unit", 1],
            ["exclude_from_sim", "no"], ["in_bom", "yes" if on_board else "no"], ["on_board", "yes" if on_board else "no"],
            ["dnp", "no"], ["uuid", Q(sym_uuid)],
            _prop("Reference", ref, x, y - 2.54, hide=not on_board), _prop("Value", value, x, y + 2.54),
            _prop("Footprint", footprint, x, y, hide=True), _prop("Datasheet", datasheet, x, y, hide=True),
            *[["pin", Q(n), ["uuid", Q(uid(sym_uuid, "pin", n))]] for n in pins],
            ["instances", ["project", Q("board"), ["path", Q("/" + root), ["reference", Q(ref)], ["unit", 1]]]]]

def _label(net, at, angle, u):
    """A global label: its net keeps the name the board gives it (a local label's net would be "/<name>")."""
    j = ["right" if angle in (180, 270) else "left"]
    return ["global_label", Q(net), ["shape", "passive"], ["at", *at, angle], ["fields_autoplaced", "yes"], _font(justify=j),
            ["uuid", Q(u)], ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", *at, 0], _font(hide=True, justify=j)]]

def _pin_types(sym):
    out = {}
    for u in sexpr.find(sym, "symbol"):
        for p in sexpr.find(u, "pin"):
            out[str(sexpr.first(p, "number")[1])] = str(p[1])
    return out

def write(path, board, parts, title=""):
    """parts: [{ref, value, footprint, symbol, uuid, block, nets: {pin: net}, datasheet}]. Writes path; returns {ref: uuid}."""
    root = uid(board, "root")
    lib = {}
    for p in parts:
        lib.setdefault(p["symbol"], symbols.get(p["symbol"]))
        # A block can correct a library pin's electrical type where its datasheet says otherwise
        # (a part's "pin_types", with "pin_types_why"): the electrical check then judges the real circuit.
        for u in sexpr.find(lib[p["symbol"]], "symbol"):
            for pin in sexpr.find(u, "pin"):
                t = p.get("pin_types", {}).get(str(sexpr.first(pin, "number")[1]))
                if t: pin[1] = t
    net_pins = {}
    for p in parts:
        for n in p["nets"].values(): net_pins[n] = net_pins.get(n, 0) + 1
    items, flags = [], []
    driven, needs = set(), set()
    # Blocks in a row of columns, each block's symbols in rows inside its box.
    blocks = []
    for p in parts:
        if p["block"] not in blocks: blocks.append(p["block"])
    bx, by, row_h, right = 20.32, 30.48, 0.0, 0.0
    for b in blocks:
        mine = [p for p in parts if p["block"] == b]
        cols = max(1, math.ceil(math.sqrt(len(mine))))
        x, y, line_h, width, placed = 0.0, 0.0, 0.0, 0.0, []
        for i, p in enumerate(mine):
            s = lib[p["symbol"]]; x0, y0, x1, y1 = symbols.size(s)
            w, h = (x1 - x0) + 25.4, (y1 - y0) + 12.7  # room for the labels on both sides
            if i and i % cols == 0: x, y, line_h = 0.0, y + line_h, 0.0
            placed.append((p, snap(x - x0 + 12.7), snap(y + y1 + 7.62)))
            x += w; line_h = max(line_h, h); width = max(width, x)
        height = y + line_h
        if bx + width > 1100: bx, by, row_h = 20.32, by + row_h + 25.4, 0.0
        items.append(["rectangle", ["start", snap(bx - 5.08), snap(by - 10.16)], ["end", snap(bx + width), snap(by + height)],
                      ["stroke", ["width", 0], ["type", "default"]], ["fill", ["type", "none"]], ["uuid", Q(uid(board, "box", b))]])
        items.append(["text", Q(b), ["exclude_from_sim", "no"], ["at", snap(bx - 2.54), snap(by - 6.35), 0],
                      _font(2.54, justify=["left", "bottom"]), ["uuid", Q(uid(board, "title", b))]])
        for p, sx, sy in placed:
            X, Y = snap(bx + sx), snap(by + sy)
            s = lib[p["symbol"]]
            pins = symbols.pins(s); types = _pin_types(s)
            items.append(_symbol(p["symbol"], p["ref"], p["value"], p["footprint"], X, Y, p["uuid"], root, list(pins), datasheet=p.get("datasheet", "")))
            for num, (px, py, a) in pins.items():
                at = [round(X + px, 4), round(Y - py, 4)]
                n = p["nets"].get(num)
                if n and net_pins.get(n, 0) > 1 or n and not n.startswith("unconnected-("):
                    la = (int(a) + 180) % 360
                    items.append(_label(n, at, la, uid(board, p["ref"], num, "label")))
                    if types.get(num) == "power_out": driven.add(n)
                    if types.get(num) == "power_in": needs.add(n)
                else:
                    items.append(["no_connect", ["at", *at], ["uuid", Q(uid(board, p["ref"], num, "nc"))]])
        right = max(right, bx + width); bx += width + 25.4; row_h = max(row_h, height + 10.16)
    # Power flags: a power net with an input but no output (fed from a connector) is driven from outside.
    flag = symbols.get("power:PWR_FLAG"); lib["power:PWR_FLAG"] = flag
    fx, fy = 20.32, snap(by + row_h + 25.4)
    for i, n in enumerate(sorted(needs - driven)):
        X = snap(fx + i * 20.32); u = uid(board, "flag", n)
        items.append(_symbol("power:PWR_FLAG", f"#FLG0{i + 1}", "PWR_FLAG", "", X, fy, u, root, ["1"], on_board=False))
        (px, py, a), = symbols.pins(flag).values()
        items.append(_label(n, [X + px, fy - py], 270, uid(board, "flaglabel", n)))
    # The smallest ISO paper the drawing fits on (with the title block's corner).
    paper = next((n for n, (w, h) in PAPER if right + 20 <= w and fy + 40 <= h), "A0")
    tree = ["kicad_sch", ["version", 20250114], ["generator", Q("circuit_harness")], ["generator_version", Q("1")],
            ["uuid", Q(root)], ["paper", Q(paper)], ["title_block", ["title", Q(title)]],
            ["lib_symbols", *lib.values()], *items,
            ["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
    open(path, "w").write(sexpr.dump(tree) + "\n")
    return root
