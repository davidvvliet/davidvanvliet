# Altair Aether: a lunar communications relay on its mass-driver sled. Every number comes from
# specs/aether.json (sourced, or a design value said to be one).
# Frame: x along the track (the direction of travel and the craft's axis, so the launch load runs
# down it), z up, y left. The craft's separation plane is at x = 0; the sled pushes from behind.
import math, os
import numpy as np
from lib import materials, parts, textures, tiling

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

X = (1, 0, 0)
# The bottom's Earth tile and X-band array: along x, and half across y (the sled's base has a pocket here).
EARTH_X, XBAND_X = 0.6, 0.8
POCKET_X, POCKET_Y = (0.47, 0.87), 0.11


def build(spec):
    d = {k: v["value"] for k, v in {**spec["facts"], **spec["dimensions"]}.items()}
    R = d["hex_corner_radius"]
    flat = R * math.cos(math.pi / 6)                 # centre to the middle of a side
    hexa = dict(segments=6, smooth=False, direction=X, roll_deg=30.0)  # a flat side facing down (-z)
    rb, ro = d["sep_ring_bolt_circle"] / 2, d["sep_ring_diameter"] / 2
    ri = rb - (ro - rb)                              # inner edge as far inside the bolts as the outer is out
    hu, hl = d["sep_ring_upper_height"], d["sep_ring_lower_height"]
    xc, t = d["cone_length"], d["deck_thickness"]   # the cone runs from the ring to the lower deck at xc
    xb = xc + d["body_length"]

    with parts.assembly("structure", core=True):
        # The separation ring's craft half, then a cone carrying the load out to the lower deck.
        parts.lathe("sep_ring_upper", [(ri, 0), (ro, 0), (ro, hu), (ri, hu)], closed=True, segments=48,
                    direction=X, material="foil_silver")
        r_top = flat - 0.04
        parts.lathe("cone", [(rb - 0.004, hu), (rb, hu), (r_top, xc), (r_top - 0.004, xc)], closed=True,
                    segments=48, direction=X, material="dark_metal")
        parts.lathe("deck_lower", [(0, xc), (R, xc), (R, xc + t), (0, xc + t)], material="white_paint", **hexa)
        parts.lathe("deck_upper", [(0, xb - t), (R, xb - t), (R, xb), (0, xb)], material="white_paint", **hexa)
        panels = parts.lathe("side_panels", [(R - 0.004, xc + t), (R, xc + t), (R, xb - t), (R - 0.004, xb - t)],
                    closed=True, material="foil_silver", **hexa)   # radiators (thermal)

    # Inside the drum, so in internal.glb: the tank on four legs, the latch valve and the lines.
    rt, hs = d["tank_diameter"] / 2, d["tank_standoff"]
    floor = xc + t                                   # the lower deck's inner face
    x0 = floor + hs + rt
    with parts.assembly("tank", internal=True):
        # Northrop Grumman 80583-1 (104 L, 83 kg hydrazine).
        prof = [(0.0, x0 - rt)] + [(rt * math.sin(math.pi * k / 24), x0 - rt * math.cos(math.pi * k / 24))
                                    for k in range(1, 24)] + [(0.0, x0 + rt)]
        parts.lathe("tank", prof, segments=48, direction=X, material="foil_silver")
        for k in range(4):
            a = math.radians(45 + 90 * k)
            y, z = 0.15 * math.cos(a), 0.15 * math.sin(a)
            top = x0 - math.sqrt(rt * rt - 0.15 ** 2) + 0.005
            parts.tube(f"tank_leg{k}", [(floor, y, z), (top, y, z)], 0.012, material="dark_metal")

    with parts.assembly("main_thruster"):
        # ArianeGroup 20 N: hung under the lower deck, firing back through the separation ring.
        L, rn = d["main_thruster_length"], d["main_thruster_nozzle"] / 2
        parts.lathe("main_thruster", [(0.0, 0.0), (0.016, 0.0), (0.016, 0.045), (0.011, 0.05), (0.011, 0.12),
                                      (0.007, 0.13), (rn, L), (rn - 0.001, L), (0.006, 0.13), (0.0, 0.125)],
                    segments=24, location=(xc, 0, 0), direction=(-1, 0, 0), material="dark_metal")

    # The sled, painted black: a pusher bulkhead bolted to the ring's lower half takes the launch load; the craft's
    # flat underside rests on the base (its weight in lunar gravity); it runs on four shoes, driven through the armature plate beneath.
    gauge, base_z = d["rail_gauge"], -flat
    with parts.assembly("sled"):
        parts.lathe("sep_ring_lower", [(ri, -hl), (ro, -hl), (ro, 0), (ri, 0)], closed=True, segments=48,
                    direction=X, material="foil_silver")
        xp = -hl - 0.02
        pusher = parts.box("pusher", (0.04, 2 * R, 2 * flat + 0.05), location=(xp, 0, 0.025), material="black")
        # The lettering on the pusher's back, the face the chase camera sees (refs/aether/sled-lettering-mask.png,
        # drawn by tools/sled_lettering.py).
        paint = materials.colour(spec["materials"]["sled_lettering"])
        img = textures.marking("aether_sled_lettering", [(os.path.join(HARNESS, "refs", "aether", "sled-lettering-mask.png"), paint)],
                               os.path.join(HARNESS, "out", "aether", "textures"))
        mat = materials.image("aether_sled_lettering", img, metallic=0.0, roughness=0.6, cutout=True)
        lw = d["sled_lettering_width"]
        parts.decal("sled_lettering", pusher, center=(xp - 0.02, 0, 0.025), direction=X, up=(0, 0, 1),
                    width=lw, height=d["sled_lettering_height"], material=mat, step=0.05, lift=0.001)
        x_end, xa = xb, xp - 0.02
        L_base = x_end - xa
        # The base is 0.12 m thick with a pocket for the Earth tile and the X-band array on the craft's bottom.
        T, (px0, px1), py, floor_t = 0.12, POCKET_X, POCKET_Y, 0.02
        zc, wb = base_z - T / 2, (gauge + 0.1) / 2
        parts.boxes("sled_base", [((px0 - xa, 2 * wb, T), ((xa + px0) / 2, 0, zc)),
                                  ((x_end - px1, 2 * wb, T), ((px1 + x_end) / 2, 0, zc)),
                                  ((px1 - px0, wb - py, T), ((px0 + px1) / 2, (wb + py) / 2, zc)),
                                  ((px1 - px0, wb - py, T), ((px0 + px1) / 2, -(wb + py) / 2, zc)),
                                  ((px1 - px0, 2 * py, floor_t), ((px0 + px1) / 2, 0, base_z - T + floor_t / 2))],
                    material="black")
        dz = T - 0.05                                # the parts under the base sit this much lower than with a 5 cm base
        for k, (sx, sy) in enumerate([(0.0, 1), (0.0, -1), (x_end - 0.1, 1), (x_end - 0.1, -1)]):
            parts.box(f"shoe{k}", (0.14, 0.1, 0.05), location=(sx, sy * gauge / 2, base_z - 0.075 - dz), material="black")
        parts.box("armature", (L_base - 0.2, 0.3, 0.03), location=((x_end + xp - 0.02) / 2, 0, base_z - 0.065 - dz),
                  material="foil_silver")

    with parts.assembly("track"):
        for k, sy in enumerate((1, -1)):
            parts.box(f"rail{k}", (4.0, 0.08, 0.12), location=(0.5, sy * gauge / 2, base_z - 0.16 - dz), material="dark_metal")
        parts.box("stator", (4.0, 0.3, 0.04), location=(0.5, 0, base_z - 0.1 - dz), material="dark_metal")

    propulsion(d, R, flat, xc, xb, t, x0, rt)
    power(d, R, flat, xc, xb)
    comms(d, R, flat, xc, xb, t)
    attitude(d, R, flat, xc, xb, t)
    electronics(d, R, flat, xc, xb, t)
    thermal(d, R, flat, xc, xb, t, x0, rt)
    finishes(spec, d, panels)
    markings(spec, d, flat, xc, xb, t, panels)
    parts.pose({name: j["angle"] for name, j in spec["joints"].items()})


def _dir(a, sign, aft, cant):
    """A thruster's firing direction at corner angle `a`: back (or forward) along x, tilted `cant`
    out from the axis, half of it round the craft (`sign`) so opposite pairs give roll."""
    rad = (0.0, math.cos(a), math.sin(a))
    tan = (0.0, -math.sin(a), math.cos(a))
    s, c = math.sin(cant), math.cos(cant)
    h = math.sqrt(0.5)
    v = (-c if aft else c, s * h * (rad[1] + sign * tan[1]), s * h * (rad[2] + sign * tan[2]))
    return v


def rcs_thruster(name, mount, direction):
    """ArianeGroup 1 N (drawing cht-1-dim-a): flow-control valve 22 mm across behind a 3.3 mm flange,
    97 mm from the fitting to the flange's face; 75 mm out to the nozzle, 30 mm across the heater's
    thermal cover. Local z runs out along `direction` from the flange's face at `mount`."""
    parts.lathe(name, [(0.0, -0.097), (0.006, -0.097), (0.006, -0.088), (0.011, -0.086), (0.011, -0.0033),
                       (0.0125, -0.0033), (0.0125, 0.006), (0.0065, 0.006), (0.0065, 0.033), (0.015, 0.033),
                       (0.015, 0.066), (0.005, 0.073), (0.0035, 0.075), (0.0, 0.075)],
                segments=20, location=mount, direction=direction, material="dark_metal")
    parts.lathe(name + "_flange", [(0.0, -0.0033), (0.033, -0.0033), (0.033, 0.0), (0.0, 0.0)],
                segments=4, smooth=False, location=mount, direction=direction, roll_deg=45.0, material="foil_silver")


def propulsion(d, R, flat, xc, xb, t, x0, rt):
    cant = math.radians(d["rcs_cant_deg"])
    corners = [math.radians(a) for a in (60, 120, 240, 300)]
    rm = 0.43                                        # the thrusters' radius, inside the corners
    ro = d["line_od"] / 2
    inlets = {}
    with parts.assembly("rcs"):
        for i, a in enumerate(corners):
            y, z = rm * math.cos(a), rm * math.sin(a)
            for aft in (True, False):
                sign = 1 if (i % 2 == 0) == aft else -1
                v = _dir(a, sign, aft, cant)
                m = (xc - 0.0033, y, z) if aft else (xb + 0.0033, y, z)
                n = f"rcs_{'a' if aft else 'f'}{i}"
                rcs_thruster(n, m, v)
                inlets[n] = tuple(m[k] - v[k] * 0.097 for k in range(3))

    # Fill and drain valves on the forward deck: nitrogen to the tank's top, hydrazine to its outlet.
    fl, tube = d["fdv_length"], 0.043
    rf = d["fdv_body_diameter"] / 2
    with parts.assembly("fill_drain"):
        for n, (y, z) in (("fdv_pressurant", (0.0, 0.0)), ("fdv_propellant", (0.0, -0.12))):
            parts.lathe(n, [(0.0, -tube), (ro, -tube), (ro, 0.0), (rf, 0.0), (rf, fl - tube - 0.012),
                            (rf * 0.7, fl - tube), (0.0, fl - tube)],
                        segments=16, location=(xb, y, z), direction=X, material="foil_silver")

    floor = xc + t
    xv = floor + 0.025                               # the lines' height over the lower deck
    xr = xb - t - 0.025                              # the forward ring, under the upper deck
    rr = 0.36
    with parts.assembly("lines", internal=True):
        # The latch valve between the tank and everything downstream.
        parts.lathe("latch_valve", [(0.0, 0.20), (0.025, 0.20), (0.025, 0.27), (0.0, 0.27)], segments=16,
                    location=(xv, 0, 0), direction=(0, 1, 0), material="dark_metal")
        parts.tube("line_outlet", [(x0 - rt, 0, 0), (xv, 0, 0), (xv, 0.2, 0)], ro, bend_radius=0.01)
        parts.tube("line_latch", [(xv, 0.27, 0), (xv, rr, 0)], ro)
        ring = lambda x: [(x, rr * math.cos(math.radians(k)), rr * math.sin(math.radians(k))) for k in range(0, 361, 10)]
        parts.tube("manifold_aft", ring(xv), ro)
        parts.tube("manifold_fwd", ring(xr), ro)
        for k, sy in enumerate((1, -1)):
            parts.tube(f"riser{k}", [(xv, sy * rr, 0), (xr, sy * rr, 0)], ro)
        for n, p in inlets.items():
            xm = xv if n.startswith("rcs_a") else xr
            a = math.atan2(p[2], p[1])
            parts.tube(f"line_{n}", [(xm, rr * math.cos(a), rr * math.sin(a)), (xm, p[1], p[2]), p], ro,
                       bend_radius=0.008)
        # The 20 N engine's feed, through the lower deck inside the cone.
        parts.tube("line_main", [(xv, 0, rr), (xv, 0, 0.33), (xc - 0.02, 0, 0.33), (xc - 0.02, 0, 0.016)], ro,
                   bend_radius=0.01)
        parts.tube("line_fill_n2", [(xb - 0.043, 0, 0), (x0 + rt, 0, 0)], ro)
        xp = xv + 0.012
        parts.tube("line_fill_n2h4", [(xb - 0.043, 0, -0.12), (xr - 0.03, 0, -0.40), (xp, 0, -0.40),
                                      (xp, 0.12, -0.12), (xp, 0.12, 0), (xv, 0.12, 0)], ro, bend_radius=0.01)


def power(d, R, flat, xc, xb):
    # Two wings, built deployed and posed folded (spec joints): a drive at each +-y corner, a yoke on a
    # hinge at the corner, then five panels along y, each hinged to the one before. Cells (AZUR
    # 3G30-Advanced 6x12, 60.7 x 124.5 mm) on the +z face, long side along x. Folded, the yoke lies
    # up the upper slanted side and the panels stack on it accordion-fashion, cells face to face in
    # pairs; the hinge lines between panels sit alternately above and below the panels so a 180°
    # fold lays each panel over the last.
    xm = (xc + xb) / 2
    cw, cl, cg = 0.0607, 0.1245, 0.0015               # cell width, length, gap
    pw, pl, pt, gap = 0.46, 0.72, 0.02, 0.02          # panel across, along x, thick; gap between panels
    zh = pt / 2 + 0.008                               # hinge lines off the panels' middle
    yoke = d["wing_yoke"]
    for sign, tag in ((1, "l"), (-1, "r")):
        with parts.assembly(f"solar_wing_{tag}"):
            y0 = sign * R                               # the corner
            parts.lathe(f"solar_drive_{tag}", [(0.0, 0.0), (0.05, 0.0), (0.05, 0.08), (0.0, 0.08)], segments=24,
                        location=(xm, y0 - sign * 0.01, 0), direction=(0, sign, 0), material="dark_metal")
            jy = parts.joint(f"yoke_{tag}_j", (xm, y0, 0), axis=X)
            yd = y0 + sign * 0.07
            yi = y0 + sign * yoke                       # the wing's inner edge
            for k, dx in enumerate((-0.25, 0.25)):
                parts.strut(f"yoke_{tag}{k}", (xm, yd, 0), (xm + dx, yi, 0), radius=0.01, material="dark_metal",
                            parent=jy)
            parts.strut(f"yoke_{tag}_bar", (xm - 0.27, yi, 0), (xm + 0.27, yi, 0), radius=0.01, material="dark_metal",
                        parent=jy)
            prev = jy
            for n in range(5):
                y_in = abs(yi) + n * (pw + gap)          # this panel's inner edge (as a distance)
                if n == 0:
                    hinge = (xm, yi, 0)
                else:
                    hinge = (xm, sign * (y_in - gap / 2), zh if n % 2 else -zh)
                jp = parts.joint(f"panel_{tag}{n}_j", hinge, axis=X, parent=prev)
                yc = sign * (y_in + pw / 2)
                parts.box(f"panel_{tag}{n}", (pl, pw, pt), location=(xm, yc, 0), material="white_paint", parent=jp)
                # The 5 x 7 cells as one sheet, the cell texture repeating once per cell and its gap
                # (finishes() gives it the texture and UVs).
                parts.box(f"cells_{tag}{n}", (5 * (cl + cg), 7 * (cw + cg), 0.002), location=(xm, yc, pt / 2 + 0.001),
                          material="solar_cell", parent=jp)
                if sign == 1 and n == 0:
                    parts.box("cell_ref", (cl, cw, 0.002), location=(xm, yc, pt / 2 + 0.0005), material="solar_cell", parent=jp)
                # Hinge brackets on the line to the panel before, one near each end.
                if n:
                    for k, dx in enumerate((-0.28, 0.28)):
                        parts.box(f"hinge_{tag}{n}{k}", (0.04, gap + 0.03, 0.012),
                                  location=(xm + dx, hinge[1], hinge[2]), material="dark_metal", parent=jp)
                prev = jp

    # Launch locks: two hold-down posts per wing on the upper slanted sides, under the folded stack.
    with parts.assembly("hold_downs"):
        for sign, tag in ((1, "l"), (-1, "r")):
            n = (0.0, sign * math.cos(math.radians(30)), math.sin(math.radians(30)))
            tv = (0.0, -sign * math.sin(math.radians(30)), math.cos(math.radians(30)))
            for k, (dx, s_) in enumerate(((-0.3, 0.12), (0.3, 0.38))):
                base = (xm + dx, n[1] * flat + tv[1] * (s_ - R / 2), n[2] * flat + tv[2] * (s_ - R / 2))
                parts.lathe(f"hold_down_{tag}{k}", [(0.0, 0.0), (0.02, 0.0), (0.02, 0.012), (0.012, 0.02),
                                                    (0.012, d["stow_gap"] - pt / 2), (0.0, d["stow_gap"] - pt / 2)],
                            segments=16, location=base, direction=n, material="dark_metal")

    # Two Saft VES16 8s4p batteries on the inside of the top and bottom side panels.
    with parts.assembly("batteries", internal=True):
        for k, sz in enumerate((1, -1)):
            parts.box(f"battery{k}", (0.308, 0.18, 0.09), location=(xm, 0, sz * (flat - 0.004 - 0.045)),
                      material="dark_metal")


def comms(d, R, flat, xc, xb, t):
    # Resized for the constellation (spec: user_array, suit_antenna, earth_array, laser_terminal, pointing_plan).
    # The craft flies nose along the motion (+x) with its top (+z) on the Moon.
    # The top, facing the Moon: the laser terminal for the craft behind at the aft end, two K-band user tiles
    # (send, receive), the S-band antenna for suits.
    with parts.assembly("user_antennas"):
        for name, y in (("user_tx", 0.1175), ("user_rx", -0.1175)):
            ka_tile(d, name, (0.66, y, flat), 1, along_x=False)
        suit_antenna(d, (0.83, -0.12, flat + 0.005))       # on the 5 mm top blanket (mli_top)
    with parts.assembly("lasers"):
        xa = xc + t + 0.01
        scot30(d, "laser_aft", (xa, 0, flat), -1)
        # The front deck: the terminal for the craft ahead, its electronics box against the deck.
        scot30(d, "laser_fore", (xb + 0.28, 0, -0.23), 1)

    # The bottom, away from the Moon: the K-band Earth tile and the X-band array (commands, safe mode).
    with parts.assembly("earth_antennas"):
        ka_tile(d, "earth_array", (EARTH_X, 0, -flat), -1, along_x=True)
        parts.box("xband_array", (0.098, 0.0826, 0.00318), location=(XBAND_X, 0, -flat - 0.00159), material="white_paint")
        # Its four 3.2 mm mounting holes, 3.2 mm in from the edges (endurosat_x4x4 Figure 2).
        hx, hy = 0.049 - 0.0032, 0.0413 - 0.0032
        for k, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
            parts.disc(f"xband_hole{k}", 0.0016, 0.0002, location=(XBAND_X + sx * hx, sy * hy, -flat - 0.00318),
                       direction=(0, 0, -1), segments=12, bevel=0.0001, material="black")
        # Its sixteen patches, 4 x 4.
        pu, pv = d["xband_patch_pitch"]
        ps = d["xband_patch_size"]
        parts.boxes("xband_patches", [((ps, ps, 0.0004), (XBAND_X + (i - 1.5) * pu, (j - 1.5) * pv, -flat - 0.00318 - 0.0002))
                                      for i in range(4) for j in range(4)], material="patch_gold")

    # The transponder hangs under the forward deck.
    with parts.assembly("radio", internal=True):
        parts.box("transponder", (0.1016, 0.1143, 0.1016), location=(xb - t - 0.0508, 0, 0.2), material="dark_metal")


def attitude(d, R, flat, xc, xb, t):
    # Faces of the hexagon (outward normals in y-z): the four slanted sides are at 30, 150, 210, 330°.
    face = lambda deg: (0.0, math.cos(math.radians(deg)), math.sin(math.radians(deg)))
    xm = (xc + xb) / 2
    # Four Blue Canyon RW4 wheels in a pyramid, one inside each slanted side, axis tilted 35° to x.
    tilt = math.radians(35)
    with parts.assembly("reaction_wheels", internal=True):
        for k, deg in enumerate((30, 150, 210, 330)):
            n = face(deg)
            sx = 1 if k % 2 == 0 else -1
            ax = (sx * math.sin(tilt), n[1] * math.cos(tilt), n[2] * math.cos(tilt))
            c = flat - 0.004 - (0.036 * math.cos(tilt) + 0.0875 * math.sin(tilt))
            centre = (xm + 0.12, n[1] * c, n[2] * c)
            base = tuple(centre[i] - ax[i] * 0.036 for i in range(3))
            parts.lathe(f"wheel{k}", [(0.0, 0.0), (0.0875, 0.0), (0.0875, 0.072), (0.03, 0.072), (0.03, 0.08),
                                      (0.0, 0.08)], segments=32, location=base, direction=tuple(-v for v in ax),
                        material="dark_metal")

    # Two Rocket Lab ST-16RT2 star trackers, large baffles, on the lower slanted sides.
    with parts.assembly("star_trackers"):
        for k, deg in enumerate((210, 330)):
            n = face(deg)
            p = (xb - 0.15, n[1] * flat, n[2] * flat)
            star_tracker(d, k, p, n)

    # Bradford coarse sun sensors on +z and +x, the Mini fine sun sensor on +z.
    with parts.assembly("sun_sensors"):
        parts.box("css_top", (0.11, 0.11, 0.03), location=(xc + 0.08, 0.185, flat + 0.015), material="dark_metal")
        parts.box("css_front", (0.03, 0.11, 0.11), location=(xb + 0.015, -0.18, 0.12), material="dark_metal")
        parts.box("fss", (0.046, 0.05, 0.017), location=(xb - 0.06, 0.12, flat + 0.0085), material="dark_metal")

    # The STIM300 IMU beside the transponder, under the forward deck.
    with parts.assembly("imu", internal=True):
        parts.box("imu", (0.022, 0.045, 0.039), location=(xb - t - 0.011, -0.15, 0.2), material="dark_metal")


def electronics(d, R, flat, xc, xb, t):
    # The AAC Clyde Space Starbuck-Mini power unit under the top panel, between the battery's end and
    # the forward deck: 147 mm along x, 249 mm across y, its width (estimated) downward.
    w = d["pcdu_width"]
    zt = flat - 0.004                                # the top panel's inner face
    x0, x1 = 0.795, 0.795 + 0.147
    xm = (xc + xb) / 2
    with parts.assembly("electronics", internal=True):
        parts.box("pcdu", (0.147, 0.249, w), location=((x0 + x1) / 2, 0, zt - w / 2), material="dark_metal")
        # Kept for the flight computer and valve drivers (designed separately): a bare plate opposite.
        parts.box("avionics_slot_plate", (0.147, 0.249, 0.005), location=((x0 + x1) / 2, 0, -zt + 0.0025),
                  material="foil_silver")
        rb = 0.008
        xh = 0.90
        for k, sy in enumerate((1, -1)):
            parts.tube(f"harness_wing{k}", [(xh, sy * 0.125, zt - 0.06), (xh, sy * 0.44, 0.03),
                                            (xm + 0.02, sy * 0.44, 0.03), (xm, sy * (R - 0.02), 0.0)], rb,
                       bend_radius=0.03, material="black")
        parts.tube("harness_bat_top", [(x0, 0.06, zt - 0.06), (0.775, 0.06, zt - 0.045)], rb, material="black")
        parts.tube("harness_bat_bottom", [(0.86, -0.125, zt - 0.1), (0.86, -0.42, 0.05), (0.86, -0.42, -0.05),
                                          (0.86, -0.13, -zt + 0.1), (0.775, -0.06, -zt + 0.045)], rb,
                   bend_radius=0.03, material="black")


def thermal(d, R, flat, xc, xb, t, x0, rt):
    # The side panels are radiators (silvered Teflon, see the structure); the top, which faces the
    # Moon, is blanketed. Film heaters round the tank's middle and on the batteries.
    with parts.assembly("blanket"):
        parts.box("mli_top", (xb - xc - 2 * t, R - 0.01, 0.005), location=((xc + xb) / 2, 0, flat + 0.0025),
                  material="foil_gold")
    xm = (xc + xb) / 2
    with parts.assembly("heaters", internal=True):
        parts.lathe("tank_heater", [(rt, x0 - 0.04), (rt + 0.001, x0 - 0.04), (rt + 0.001, x0 + 0.04), (rt, x0 + 0.04)],
                    closed=True, segments=48, direction=X, material="foil_gold")
        for k, sz in enumerate((1, -1)):
            zf = sz * (flat - 0.004 - 0.09 - 0.0005)
            parts.box(f"battery_heater{k}", (0.25, 0.14, 0.001), location=(xm, 0, zf), material="foil_gold")



def markings(spec, d, flat, xc, xb, t, panels):
    # "Altair AETHER" on the two lower slanted sides, under the US flag (as on the finrocket), turned so
    # they read upright in flight (the craft rolls over before the burn, its top to the Moon). The top carries the user tiles, the bottom the Earth tile.
    col = lambda k: materials.colour(spec["materials"][k])
    out = os.path.join(HARNESS, "out", "aether", "textures")
    img = textures.marking("aether_craft_lettering",
                           [(os.path.join(HARNESS, "refs", "aether", "craft-lettering-mask.png"), col("craft_lettering"))], out)
    mat = materials.image("aether_craft_lettering", img, metallic=0.0, roughness=0.6, cutout=True)
    fl = os.path.join(HARNESS, "refs", "finrocket")   # the flag masks drawn for the finrocket (us_flag)
    flag = textures.marking("aether_flag", [(os.path.join(fl, "flag-field.png"), col("flag_white")),
                                            (os.path.join(fl, "flag-red.png"), col("flag_red")),
                                            (os.path.join(fl, "flag-blue.png"), col("flag_blue")),
                                            (os.path.join(fl, "flag-stars.png"), col("flag_white"))], out)
    flag_mat = materials.image("aether_flag", flag, metallic=0.0, roughness=0.5)
    ratio = d["craft_lettering_side_height"] / d["craft_lettering_side_width"]
    fh = d["craft_flag_hoist"]
    # Along x, the sides are clear from the lower deck to the star trackers' baffles.
    xs = (xc + t + xb - 0.15 - 0.05) / 2
    with parts.assembly("markings"):
        for k, deg in enumerate((210, 330)):
            a = math.radians(deg)
            n = (0.0, math.cos(a), math.sin(a))
            v = (0.0, math.sin(a), -math.cos(a)) if deg == 330 else (0.0, -math.sin(a), math.cos(a))  # down the side: up in flight
            on = lambda off: (xs, n[1] * flat + v[1] * off, n[2] * flat + v[2] * off)
            inward = (0.0, -n[1], -n[2])
            # The flag's left edge on the left edge of "Altair" (the mask's 30 px margin in from its left).
            right = (inward[1] * v[2] - inward[2] * v[1], inward[2] * v[0] - inward[0] * v[2], inward[0] * v[1] - inward[1] * v[0])
            lw = d["craft_lettering_side_width"]
            shift = -lw / 2 + lw * 30 / 1102 + 1.9 * fh / 2
            c = on(d["craft_flag_offset"])
            parts.decal(f"craft_flag{k}", panels, center=tuple(c[i] + right[i] * shift for i in range(3)), direction=inward, up=v,
                        width=1.9 * fh, height=fh, material=flag_mat, step=0.02, lift=0.001)
            parts.decal(f"craft_lettering{k}", panels, center=on(d["craft_lettering_side_offset"]), direction=inward,
                        up=v, width=d["craft_lettering_side_width"], height=d["craft_lettering_side_height"],
                        material=mat, step=0.02, lift=0.001)



def star_tracker(d, k, base, n):
    """Rocket Lab ST-16RT2 with the large baffle (rl_st16rt2 photo, scaled by its 99 x 120 mm): a black square
    electronics base, a round flange with six bolts, and the bare aluminium cone baffle, black inside.
    `base`: the middle of its mounting face; `n`: the way it looks."""
    sh = d["star_tracker_shape"]
    bw, bh = sh["base"]
    fr, ft = sh["flange"]
    r0, r1, L = sh["cone_foot"], 0.0495, 0.12
    z0 = bh + ft                                       # where the cone starts
    wall = 0.0015
    parts.prism(f"star_tracker{k}_base", 4, bw / math.sqrt(2), bh, location=base, direction=n, roll_deg=45,
                material="dark_metal")
    parts.lathe(f"star_tracker{k}", [(0.0, 0.0), (fr, 0.0), (fr, z0), (r0, z0), (r1, L), (r1 - wall, L),
                                     (r0 - wall, z0 + 0.002), (0.0, z0 + 0.002)],
                segments=32, location=base, direction=n, material="baffle_aluminium")
    parts.lathe(f"star_tracker{k}_inside", [(0.0, z0 + 0.0025), (r0 - wall - 0.0004, z0 + 0.0025),
                                            (r1 - wall - 0.0004, L - 0.0005)],
                segments=32, location=base, direction=n, material="black")
    # Six bolts round the flange.
    u = (1.0, 0.0, 0.0)
    v = (n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0])
    rb = (fr + r0) / 2
    pts = []
    for i in range(6):
        a = math.radians(30 + 60 * i)
        pts.append(tuple(base[j] + n[j] * z0 + rb * (math.cos(a) * u[j] + math.sin(a) * v[j]) for j in range(3)))
    for i, q in enumerate(pts):
        parts.cylinder(f"star_tracker{k}_bolt{i}", 0.0015, 0.0018, location=q, direction=n, segments=8,
                       material="foil_silver")


def suit_antenna(d, base):
    """EnduroSat S-band wideband antenna (endurosat_s_wide gallery photos): two white ceramic plates stacked
    with a gold layer between, the corners notched, a large round gold patch in the middle and four smaller
    ones at the middle of the edges, two screws per edge. `base`: the middle of its back, on the top face."""
    sh = d["suit_antenna_layout"]
    w, (pt, gt), nt = sh["board"], sh["plates"], sh["notch"]
    bx, by, bz = base
    cross = lambda z0, h, mat, name: parts.boxes(name, [((w, w - 2 * nt, h), (bx, by, z0 + h / 2)),
                                                         ((w - 2 * nt, w, h), (bx, by, z0 + h / 2))], material=mat)
    cross(bz, pt, "white_paint", "suit_antenna")
    cross(bz + pt, gt, "patch_gold", "suit_antenna_layer")
    cross(bz + pt + gt, pt, "white_paint", "suit_antenna_top")
    top = bz + 2 * pt + gt
    (dc, ds), off = sh["patches"], sh["side_offset"]
    parts.disc("suit_patch0", dc / 2, 0.0002, location=(bx, by, top), segments=32, bevel=0.0001, material="patch_gold")
    for i, (sx, sy) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
        parts.disc(f"suit_patch{i + 1}", ds / 2, 0.0002, location=(bx + sx * off, by + sy * off, top), segments=32,
                   bevel=0.0001, material="patch_gold")
    sa, si = sh["screws"]
    e = w / 2 - si
    heads = [(sx * sa, e * sy) for sx in (-1, 1) for sy in (-1, 1)] + [(e * sx, sy * sa) for sx in (-1, 1) for sy in (-1, 1)]
    parts.boxes("suit_antenna_screws", [((0.003, 0.003, 0.0008), (bx + hx, by + hy, top + 0.0004)) for hx, hy in heads],
                material="foil_silver")


def ka_tile(d, name, base, up, along_x):
    """Boeing's smallsat Ka tile (nasa_ka_smallsat p. 24 drawing): a mounting flange the full 22.9 x 17.8 cm,
    the housing stepped in from it, and the square radome flush in its top face. `base`: the middle of
    its back face; `up`: +1 facing +z, -1 facing -z; the 22.9 cm side along x or y."""
    L, W, H = 0.229, 0.178, 0.096
    lx, ly = (L, W) if along_x else (W, L)
    fl, step, rin = d["ka_tile_flange"], d["ka_tile_step"], d["ka_tile_radome_inset"]
    bx, by, bz = base
    z = lambda a, b: bz + up * (a + b) / 2           # middle of a span a..b off the back face
    parts.boxes(name, [((lx, ly, fl), (bx, by, z(0, fl))),
                       ((lx - 2 * step, ly - 2 * step, H - fl), (bx, by, z(fl, H)))], material="foil_silver")
    parts.box(f"{name}_radome", (lx - 2 * step - 2 * rin, ly - 2 * step - 2 * rin, 0.003),
              location=(bx, by, z(H - 0.0025, H + 0.0005)), material="white_paint")


def scot30(d, name, end, s):
    """Tesat SCOT30 (tesat_scot30 photo): a base plate, the electronics box at the back, and at the front
    (the end facing the link, `s` = -1 or +1 along x) a pedestal carrying the two-axis head with its window.
    `end`: the middle of the base plate's front edge, on its underside. 280 along x, 230 across, 200 tall."""
    ex, ey, ez = end
    sh = d["scot30_layout"]
    X_ = lambda u: ex - s * u                         # u: distance back from the front edge
    bp, (b0, bh, bw), (pu, pr, ph), (hr, hl, tilt) = sh["plate"], sh["box"], sh["pedestal"], sh["head"]
    parts.boxes(name, [((0.28, 0.23, bp), (X_(0.14), ey, ez + bp / 2)),
                       ((0.28 - b0, bw, bh), (X_((b0 + 0.28) / 2), ey, ez + bp + bh / 2))], material="foil_silver")
    parts.lathe(f"{name}_pedestal", [(0.0, 0.0), (pr * 1.25, 0.0), (pr * 1.25, 0.018), (pr, 0.018), (pr, ph - 0.015),
                                     (pr * 1.12, ph - 0.015), (pr * 1.12, ph), (0.0, ph)],
                segments=32, location=(X_(pu), ey, ez + bp), direction=(0, 0, 1), material="foil_silver")
    # The head: a drum leaning towards the link, its window on the end.
    a = math.radians(tilt)
    axis = (s * math.cos(a), 0.0, math.sin(a))
    hc = (X_(pu), ey, ez + bp + ph + hr * 0.9)
    tip = tuple(hc[i] + axis[i] * hl / 2 for i in range(3))
    parts.lathe(f"{name}_head", [(0.0, -hl / 2), (hr, -hl / 2), (hr, hl / 2), (0.0, hl / 2)], segments=32,
                location=hc, direction=axis, material="foil_silver")
    parts.lathe(f"{name}_window", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.002), (0.0, 0.002)], segments=32,
                location=tip, direction=axis, material="laser_glass")


def _face_uv(obj, along, repeat_u, repeat_v):
    """UVs for flat faces: u along `along` (world), v across each face in its own plane (normal x along),
    so strips laid along `along` keep their width on slanted faces."""
    from mathutils import Vector
    me, mw = obj.data, obj.matrix_world
    a = Vector(along).normalized()
    n3 = mw.to_3x3()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = (n3 @ poly.normal).normalized()
        c = n.cross(a)
        if c.length < 1e-6:
            c = Vector((0, 0, 1)).cross(a)
        c.normalize()
        for li in poly.loop_indices:
            p = mw @ me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (p.dot(a) / repeat_u, p.dot(c) / repeat_v)


def _hex(name):
    """The sRGB hex of a material as built (the shared palette or the spec's entry)."""
    col = materials.definition(name)[0]
    enc = [c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055 for c in col]
    return "#" + "".join(f"{round(min(max(e, 0), 1) * 255):02x}" for e in enc)


def solar_cell_tile(d, spec):
    """One AZUR 3G30A assembly and its share of the gaps, as seen on the datasheet photo (azur_3g30c):
    dark cell, two corners cut off along one long edge, a busbar inside that edge dipping towards its
    middle, two in-plane interconnects across the gap to the next cell, the bypass diode in one cut corner.
    Long side along u. Returns (base, normal)."""
    cw, cl, cg = d["cell_width"], d["cell_length"], d["cell_gap"]
    pu, pv, px = cl + cg, cw + cg, 4000                  # tile metres; pixels per metre
    w, h = round(pu * px), round(pv * px)
    U, V = np.meshgrid((np.arange(w) + 0.5) / w * pu, (np.arange(h) + 0.5) / h * pv)  # rows bottom-up: v up
    x, y = U - cg / 2, V - cg / 2                        # from the cell's lower left corner
    chu, chv = d["cell_chamfer"]
    top = y - cw                                          # <= 0 inside, below the top edge
    cut = np.maximum(chu - x, x - (cl - chu)) / chu * chv  # how far the top corner's cut reaches down
    inside = (x >= 0) & (x <= cl) & (y >= 0) & (y <= cw) & (top <= -np.maximum(cut, 0))
    # The busbar: inset along the top edge and the cuts, dipping by `dip` at the middle.
    inset, bw, dip = d["cell_busbar_inset"], d["cell_busbar_width"], d["cell_busbar_dip"]
    edge = cw - np.maximum(cut, 0) - inset - dip * np.clip(1 - np.abs(x - cl / 2) / (cl / 2 - chu), 0, 1)
    bus = inside & (np.abs(y - edge) < bw / 2) & (x > inset) & (x < cl - inset)
    tab = np.zeros_like(inside)
    for xi in d["cell_interconnect_x"]:
        tw = d["cell_interconnect_width"]
        tab |= (np.abs(x - xi) < tw / 2) & ((y > edge) | (y < 0))
    diode = (x > cl - chu * 0.85) & (x < cl - chu * 0.25) & (top > -chv * 0.75) & (top < -chv * 0.2) & ~inside & (y < cw)
    cell = tiling.srgb(spec["materials"]["solar_cell"]["hex"])
    silver = tiling.srgb(_hex("foil_silver"))
    rgb = np.where(inside[..., None], cell[None, None], tiling.srgb(_hex("white_paint"))[None, None])
    rgb = np.where((bus | tab | diode)[..., None], silver[None, None], rgb)
    hgt = (bus | tab).astype(np.float32) * 0.5 + inside * 0.3
    gy, gx = np.gradient(hgt)
    nrm = np.stack([-gx * 2, -gy * 2, np.ones_like(hgt)], 2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return (tiling.image("aether", "solar_cell_base", rgb.astype(np.float32), "sRGB"),
            tiling.image("aether", "solar_cell_normal", (nrm * 0.5 + 0.5).astype(np.float32), "Non-Color"))


def tape_strips(d, n=10, px=1000, seed=4):
    """Silvered-Teflon tape laid in strips `radiator_tape_width` wide along u, each overlapping the last
    a little (a faint line), each lying at its own slight tilt so the strips catch the light one by one.
    Repeats every n strips across. Returns (base, normal)."""
    sw = d["radiator_tape_width"]
    w, h = 64, round(n * sw * px)
    V = (np.arange(h) + 0.5) / px
    k = (V // sw).astype(int)
    f = (V % sw) / sw
    rng = np.random.default_rng(seed)
    tilt = rng.uniform(-1, 1, n)[k] * np.tan(np.radians(2.0))
    bow = (f - 0.5) * np.tan(np.radians(1.5))         # each strip bows a little across
    seam = np.clip(1 - np.minimum(f, 1 - f) * sw * px / 1.5, 0, 1)
    shade = (1 + 0.03 * rng.uniform(-1, 1, n)[k]) * (1 - 0.25 * seam)
    rgb = tiling.srgb(_hex("foil_silver"))[None, None] * np.repeat(shade[:, None, None], w, 1)
    sy = np.repeat((tilt + bow)[:, None], w, 1)
    nrm = np.stack([np.zeros_like(sy), -sy, np.ones_like(sy)], 2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return (tiling.image("aether", "radiator_tape_base", np.clip(rgb, 0, 1).astype(np.float32), "sRGB"),
            tiling.image("aether", "radiator_tape_normal", (nrm * 0.5 + 0.5).astype(np.float32), "Non-Color"))


def finishes(spec, d, panels):
    # The cells' texture, the radiators' tape strips and the top blanket's crinkled foil.
    sc = spec["materials"]["solar_cell"]
    cb, cn = solar_cell_tile(d, spec)
    cell_mat = materials.image("aether_solar_cells", cb, normal=cn, metallic=sc["metallic"], roughness=sc["roughness"])
    pu, pv = d["cell_length"] + d["cell_gap"], d["cell_width"] + d["cell_gap"]
    for obj in list(parts.collection().objects):
        if obj.type == "MESH" and obj.name.startswith("cells_"):
            obj.data.materials[0] = cell_mat
            me, mw = obj.data, obj.matrix_world
            lo = min((mw @ v.co).x for v in me.vertices), min((mw @ v.co).y for v in me.vertices)
            uv = me.uv_layers.new(name="UVMap")
            for li, loop in enumerate(me.loops):
                p = mw @ me.vertices[loop.vertex_index].co
                uv.data[li].uv = ((p.x - lo[0]) / pu, (p.y - lo[1]) / pv)
    _, sm, sr = materials.definition("foil_silver")
    tb, tn = tape_strips(d)
    panels.data.materials[0] = materials.image("aether_radiator_tape", tb, normal=tn, metallic=sm, roughness=sr)
    _face_uv(panels, (1, 0, 0), 64 / 1000, 10 * d["radiator_tape_width"])
    _, gm, gr = materials.definition("foil_gold")
    fb, fn = tiling.crinkled_foil("aether", "mli_foil", _hex("foil_gold"), facet=0.04, tilt_deg=8, wrinkle=0.15,
                                  wrinkle_deg=6, spread=0.06, stretch=1.4, pillow=0.25, pillow_deg=10,
                                  repeat=(0.5, 0.5), px_per_m=700)
    mli = parts.collection().objects["mli_top"]
    mli.data.materials[0] = materials.image("aether_mli", fb, normal=fn, metallic=gm, roughness=gr)
    tiling.box_uv(mli, 0.5)
