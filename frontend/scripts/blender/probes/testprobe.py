# Harness fixture: one of every shared part, so a change to lib/ shows on its sheet.
from lib import parts

def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    bus = parts.prism("bus", sides=10, radius=0.9, height=d["bus_height"], location=(0, 0, -0.25),
                      material="foil_gold")
    parts.dish("dish", diameter=d["dish_diameter"], depth=0.45, location=(0, 0, 0.25))
    parts.boom("boom", length=d["boom_length"], width=0.18, location=(0.9, 0, 0), direction=(1, 0, 0))
    parts.boom("rtg_arm", length=1.0, width=0.06, truss=False, location=(-0.9, 0, 0),
               direction=(-1, 0, 0))
    parts.rtg("rtg", length=d["rtg_length"], radius=0.2, location=(-1.92, -0.55, 0),
              direction=(0, 1, 0))
    parts.cylinder("antenna", radius=0.02, length=0.6, location=(0, 0, 0.25), segments=8,
                   material="white_paint")
    parts.panel("radiator", 0.6, 0.4, location=(0, -0.92, 0), direction=(0, -1, 0),
                material="foil_silver")
    parts.box("instrument", (0.3, 0.25, 0.2), location=(4.9, 0, 0.2), material="black")
