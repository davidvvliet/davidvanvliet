# Shared spacecraft parts. Every part is one mesh object in the "Probe" collection,
# built with bmesh (no operators, so it works headless and in the live session alike).
# Units are metres. A part's local +Z is its axis: `direction` aims it, `location` is
# its base (dish vertex, boom root, cylinder bottom).
#
# The parts live in four files by kind; this module gathers them, so every probe and lib module
# keeps using `parts.<name>`. Add a new part to the file it belongs in:
#   parts_core.py    the collection, assemblies, _object (bmesh -> object), joints and poses
#   parts_shapes.py  basic shapes: cylinder, box, dish, boom, rtg, plate, lathe, wheel, tube...
#   parts_aero.py    lofted bodies and lifting surfaces: section, loft, fuselage, surface, grid_fin
#   parts_skin.py    operations on a skin: cap_hole, shell, decal
import importlib

from . import parts_core, parts_shapes, parts_aero, parts_skin

# Reloading this module (build.py does, so the live session picks up edits) reloads its parts,
# core first: the others take their helpers from it.
for _m in (parts_core, parts_shapes, parts_aero, parts_skin):
    importlib.reload(_m)
    globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
del _m
