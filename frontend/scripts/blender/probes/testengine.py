# Harness fixture: lib/engines.py's rocket (full and simple), a traced nozzle and a jet, so a
# change to the engine code shows on this sheet.
from lib import engines

def build(spec):
    engines.build(spec["engine"], "rocket", lod="full")
    engines.place(spec["engine"], "rocket_simple", location=(2.5, 0, 0), lod="simple")
    engines.place(spec["traced"], "traced", location=(-2.0, 0, 0), lod="full")
    engines.place(spec["jet"], "jet", location=(0, 1.5, 1.0), direction=(0, 1, 0), lod="full")
