# Schematic symbols by library id ("Device:R"), flattened (a symbol that extends another gets the
# other's drawing and pins), as a schematic's lib_symbols needs them. Looked up in the schematics of
# imported boards first (their designers' own symbols, embedded and already flattened), then in
# KiCad's symbol libraries.
import copy, glob, os
from . import sexpr, tools

SYMBOLS = os.path.join(tools.KICAD_APP, "Contents", "SharedSupport", "symbols")
_embedded, _libs = None, {}

def _embedded_symbols():
    global _embedded
    if _embedded is None:
        _embedded = {}
        for sch in glob.glob(os.path.join(tools.HARNESS, "boards", "*", "*.kicad_sch")):
            tree = sexpr.parse(open(sch).read())[0]
            for s in sexpr.find(sexpr.first(tree, "lib_symbols") or [], "symbol"):
                _embedded.setdefault(str(s[1]), s)
    return _embedded

def _library(lib):
    if lib not in _libs:
        path = os.path.join(SYMBOLS, f"{lib}.kicad_sym")
        tree = sexpr.parse(open(path).read())[0] if os.path.exists(path) else []
        _libs[lib] = {str(s[1]): s for s in sexpr.find(tree, "symbol")}
    return _libs[lib]

def _flatten(lib, name):
    syms = _library(lib)
    if name not in syms: return None
    s = copy.deepcopy(syms[name])
    ext = sexpr.first(s, "extends")
    if not ext: return s
    base = _flatten(lib, str(ext[1]))
    out = [c for c in base if not (isinstance(c, list) and c and c[0] == "property")]
    out[1] = sexpr.Q(name)
    props = sexpr.find(s, "property")
    at = next(i for i, c in enumerate(out) if isinstance(c, list) and c and c[0] == "symbol")
    out[at:at] = props  # the derived symbol's own properties, then the base's drawing units
    for c in out:  # units are named after the symbol: "Base_1_1" -> "Name_1_1"
        if isinstance(c, list) and c and c[0] == "symbol":
            c[1] = sexpr.Q(name + str(c[1])[len(str(base[1])):])
    return out

def get(lib_id):
    """The flattened symbol for `lib_id`, named `lib_id` as in a schematic's lib_symbols."""
    if lib_id in _embedded_symbols():
        return copy.deepcopy(_embedded_symbols()[lib_id])
    lib, _, name = lib_id.partition(":")
    s = _flatten(lib, name)
    if s is None:
        raise KeyError(f"symbol {lib_id} not in KiCad's library or an imported board's schematic")
    s[1] = sexpr.Q(lib_id)
    return s

def pins(sym, unit=1):
    """{pin number: (x, y, angle)} of a flattened symbol's unit (and its common unit 0), symbol units."""
    out = {}
    for u in sexpr.find(sym, "symbol"):
        parts = str(u[1]).rsplit("_", 2)
        if len(parts) == 3 and parts[1] not in ("0", str(unit)): continue
        for p in sexpr.find(u, "pin"):
            at = sexpr.first(p, "at"); num = sexpr.first(p, "number")
            out[str(num[1])] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
    return out

def pin_names(sym):
    """{pin number: pin name} of a flattened symbol."""
    return {str(sexpr.first(p, "number")[1]): str(sexpr.first(p, "name")[1])
            for u in sexpr.find(sym, "symbol") for p in sexpr.find(u, "pin")}

def size(sym):
    """(min x, min y, max x, max y) of the symbol's pins and rectangles, symbol units (y up)."""
    xs, ys = [0.0], [0.0]
    for u in sexpr.find(sym, "symbol"):
        for p in sexpr.find(u, "pin"):
            at = sexpr.first(p, "at"); xs.append(float(at[1])); ys.append(float(at[2]))
        for r in sexpr.find(u, "rectangle"):
            for k in ("start", "end"):
                c = sexpr.first(r, k); xs.append(float(c[1])); ys.append(float(c[2]))
    return min(xs), min(ys), max(xs), max(ys)
