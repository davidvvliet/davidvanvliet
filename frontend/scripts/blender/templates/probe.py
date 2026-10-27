# __TITLE__. Built from lib/parts in metres; every number comes from specs/__PROBE__.json
# (with its source) or is marked here as estimated from a reference image.
from lib import parts

def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    parts.dish("dish", diameter=d["example_dish_diameter"], depth=0.15)
