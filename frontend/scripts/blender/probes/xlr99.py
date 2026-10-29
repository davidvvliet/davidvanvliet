# Reaction Motors XLR99, the X-15's engine: built by lib/engines.py from the spec's "engine"
# block (every number sourced there).
from lib import engines

def build(spec):
    with engines.parts.assembly("xlr99", core=True):
        engines.build(spec["engine"], "xlr99", lod="full")
