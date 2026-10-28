# Harness fixture: a small aeroplane exercising fuselage (loft through sections), surface
# (lens wings and tail, a wedge fin) and loft (a canopy). Frame: x forward, y left, z up.
# Design values, not a real aircraft. Also two painted decals: one on the flat-ish side, one
# wrapped over the curved top.
import os
from lib import materials, parts, textures

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build(spec):
    with parts.assembly("fuselage", core=True):
        body = parts.fuselage("fuselage", [(4.0, 0, 0.05, -0.05), (3.4, 0.25, 0.25, -0.25), (2.0, 0.5, 0.45, -0.5),
                                    (-2.0, 0.5, 0.45, -0.5, 3.0), (-3.0, 0.3, 0.3, -0.3)])
    with parts.assembly("canopy"):
        parts.loft("canopy", [[(2.6, 0, 0.42)],
                              [(2.0, y, z) for y, z in parts.section(0.3, 0.75, 0.35)],
                              [(0.8, y, z) for y, z in parts.section(0.3, 0.7, 0.35)],
                              [(0.0, 0, 0.42)]], material="black")
    for sign, side in parts.sides():
        with parts.assembly(f"wing_{side}"):
            parts.surface(f"wing_{side}", (1.0, sign * 0.45, 0), 2.0, (-0.6, sign * 3.0, 0), 0.6, 0.06)
        with parts.assembly(f"htail_{side}"):
            parts.surface(f"htail_{side}", (-1.8, sign * 0.3, 0.1), 1.0, (-2.6, sign * 1.3, -0.1), 0.4, 0.06)
    with parts.assembly("fin"):
        parts.surface("fin", (-1.6, 0, 0.4), 1.4, (-2.4, 0, 1.6), 0.8, 0.1, kind="wedge")
    paint = materials.colour(spec["materials"]["decal_paint"])
    img = textures.marking("testplane_decal", [(os.path.join(HARNESS, "refs", "testplane", "decal-mask.png"), paint)],
                           os.path.join(HARNESS, "out", "testplane", "textures"))
    mat = materials.image("testplane_decal", img, metallic=0.0, roughness=0.5, cutout=True)
    with parts.assembly("decal_side"):
        parts.decal("decal_side", body, center=(0.0, 0.5, 0.0), direction=(0, -1, 0), up=(0, 0, 1),
                    width=1.2, height=0.6, material=mat)
    with parts.assembly("decal_top"):
        parts.decal("decal_top", body, center=(3.0, 0.0, 0.3), direction=(0, 0, -1), up=(1, 0, 0),
                    width=0.6, height=0.4, material=mat)
