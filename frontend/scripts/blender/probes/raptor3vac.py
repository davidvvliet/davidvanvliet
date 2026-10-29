# SpaceX Raptor 3 Vacuum, Starship V3's vacuum engine: built by lib/engines.py from the spec's
# "engine" block (every number sourced there).
from lib import engines

def build(spec):
    with engines.parts.assembly("raptor3vac", core=True):
        engines.build(spec["engine"], "raptor3vac", lod="full")
