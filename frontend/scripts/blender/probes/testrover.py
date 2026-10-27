# Harness fixture: a six-wheeled rover with rocker-bogie suspension, an arm and a mast,
# exercising wheel, tube, lathe, joints, chain, assemblies, distance/ground/joint checks.
# Frame: z up, ground at z = 0, forward +y, left +x. Design values, not a real rover.
from lib import parts

WHEEL_D, WHEEL_W, CLEAT = 0.5, 0.25, 0.01
WHEEL_Z = WHEEL_D / 2 + CLEAT                 # cleats rest on the ground
WHEEL_X = 0.65
WHEEL_Y = {"front": 0.6, "middle": 0.0, "rear": -0.6}

def build(spec):
    with parts.assembly("body", core=True):
        parts.box("body", (1.0, 1.4, 0.4), location=(0, 0, 0.75), material="body_paint")

    for sign, side in parts.sides():
        x_arm = sign * 0.55
        pivot = (x_arm, 0.1, 0.7)
        with parts.assembly(f"rocker_{side}"):
            parts.cylinder(f"rocker_pivot_{side}", 0.04, 0.06, location=(sign * 0.5, 0.1, 0.7),
                           direction=(sign, 0, 0), material="dark_metal")
            rocker = parts.joint(f"rocker_{side}_j", pivot, axis=(1, 0, 0))
            bogie_pivot = (x_arm, -0.3, 0.45)
            # Rocker: from the pivot forward and down to the front wheel, and back to the bogie.
            parts.tube(f"rocker_{side}", [(x_arm, WHEEL_Y["front"], WHEEL_Z), (x_arm, 0.45, 0.62), pivot,
                                          bogie_pivot], 0.03, bend_radius=0.08, parent=rocker)
        with parts.assembly(f"bogie_{side}"):
            bogie = parts.joint(f"bogie_{side}_j", bogie_pivot, axis=(1, 0, 0), parent=rocker)
            parts.tube(f"bogie_{side}", [(x_arm, WHEEL_Y["middle"], WHEEL_Z), bogie_pivot,
                                         (x_arm, WHEEL_Y["rear"], WHEEL_Z)], 0.03, bend_radius=0.06, parent=bogie)
        for pos, y in WHEEL_Y.items():
            with parts.assembly(f"wheel_{side}_{pos}"):
                parts.wheel(f"wheel_{side}_{pos}", WHEEL_D, WHEEL_W, location=(sign * WHEEL_X, y, WHEEL_Z),
                            axle=(sign, 0, 0), cleats=24, cleat_height=CLEAT, spokes=6,
                            parent=rocker if pos == "front" else bogie)

    with parts.assembly("mast"):
        mj = parts.chain("mast", base=(0.3, 0.55, 0.95), direction=(0, 0, 1),
                         links=[{"length": 1.0, "radius": 0.04, "axis": (1, 0, 0)}])
        parts.lathe("mast_head", [(0, 1.95), (0.1, 1.95), (0.12, 2.05), (0.1, 2.15), (0, 2.15)],
                    location=(0.3, 0.55, 0), material="white_paint", parent=mj[0])
    with parts.assembly("arm"):
        parts.chain("arm", base=(0, 0.7, 0.7), direction=(0, 1, 0),
                    links=[{"length": 0.5, "radius": 0.03, "axis": (1, 0, 0)},
                           {"length": 0.4, "radius": 0.025, "axis": (1, 0, 0)}])

    parts.pose({name: j["angle"] for name, j in spec["joints"].items()})
