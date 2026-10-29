# SpaceX Raptor 3, the sea-level engine of Super Heavy Block 3: built by lib/engines.py from the
# spec's "engine" block (every number sourced there), plus the serial painted on the bell: one
# sheet laid on the skin, kept only inside the numeral's blocks, so its edges are geometry and
# stay sharp.
import bpy
from lib import engines, parts

def build(spec):
    with parts.assembly("raptor3", core=True):
        engines.build(spec["engine"], "raptor3", lod="full")
    for d in spec.get("decals", []):
        with parts.assembly(f"raptor3_{d['name']}"):
            parts.decal(f"raptor3_{d['name']}", bpy.data.objects[f"raptor3_{d['on']}"], d["center"],
                        d["direction"], d["up"], d["width"], d["height"], d["material"],
                        shapes=list(d["shapes"].values()))
