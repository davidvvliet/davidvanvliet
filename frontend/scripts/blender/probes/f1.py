# Rocketdyne F-1, the Saturn V first-stage engine: built by lib/engines.py from the spec's
# "engine" block (every number sourced there).
from lib import engines

def build(spec):
    with engines.parts.assembly("f1", core=True):
        engines.build(spec["engine"], "f1", lod="full")
