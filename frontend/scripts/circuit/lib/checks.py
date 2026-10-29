# KiCad's own checks, as rows for the dashboard's check table (the shape the Blender harness uses:
# name, ok, measured, expected, unit, detail). Errors fail a build; warnings are listed, never fail it.
#   design rules (DRC): clearances, widths, holes, shorts, and every connection the schematic asks for
#   electrical (ERC): the schematic itself (unconnected pins, outputs driving each other, unpowered pins)
import collections, json, os, subprocess, tempfile
from . import tools

def _rows(name, violations, extra_errors=0):
    by = collections.Counter((v["severity"], v["type"]) for v in violations)
    errors = sum(n for (s, _), n in by.items() if s == "error") + extra_errors
    warnings = sum(n for (s, _), n in by.items() if s == "warning")
    top = ", ".join(f"{t} ×{n}" for (s, t), n in by.most_common() if s == "error")
    return [{"name": f"{name}: errors", "ok": errors == 0, "measured": errors, "expected": 0, "unit": "errors", "detail": top},
            {"name": f"{name}: warnings", "ok": True, "measured": warnings, "expected": 0, "unit": "warnings",
             "detail": ", ".join(f"{t} ×{n}" for (s, t), n in by.most_common() if s == "warning")}]

def drc(pcb):
    """Design rule check of a .kicad_pcb (its .kicad_pro beside it holds the rules)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "drc.json")
        subprocess.run([tools.tool("kicad-cli"), "pcb", "drc", "--format", "json", "--schematic-parity", "-o", out, pcb],
                       capture_output=True, text=True)
        d = json.load(open(out))
    unconnected = len(d.get("unconnected_items", []))
    parity = len(d.get("schematic_parity", []))
    rows = _rows("design rules", d.get("violations", []))
    rows.insert(1, {"name": "unconnected", "ok": unconnected == 0, "measured": unconnected, "expected": 0, "unit": "connections"})
    rows.insert(2, {"name": "schematic matches board", "ok": parity == 0, "measured": parity, "expected": 0, "unit": "differences"})
    return rows

def erc(sch):
    """Electrical rules check of a .kicad_sch."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "erc.json")
        subprocess.run([tools.tool("kicad-cli"), "sch", "erc", "--format", "json", "-o", out, sch], capture_output=True, text=True)
        d = json.load(open(out))
    return _rows("electrical", [v for s in d.get("sheets", []) for v in s.get("violations", [])])
