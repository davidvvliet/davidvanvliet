# Altair Aether: a lunar communications relay on its mass-driver sled. Every number comes from
# specs/aether.json (sourced, or a design value said to be one).
# Frame: x along the track (the direction of travel and the craft's axis, so the launch load runs
# down it), z up, y left. The craft's separation plane is at x = 0; the sled pushes from behind.
import math
from lib import parts

X = (1, 0, 0)


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
        parts.lathe("side_panels", [(R - 0.004, xc + t), (R, xc + t), (R, xb - t), (R - 0.004, xb - t)],
                    closed=True, material="foil_gold", **hexa)

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

    # The sled: a pusher bulkhead bolted to the ring's lower half takes the launch load; the craft's
    # flat underside rests on the base (its weight in lunar gravity); it runs on four shoes, driven through the armature plate beneath.
    gauge, base_z = d["rail_gauge"], -flat
    with parts.assembly("sled"):
        parts.lathe("sep_ring_lower", [(ri, -hl), (ro, -hl), (ro, 0), (ri, 0)], closed=True, segments=48,
                    direction=X, material="foil_silver")
        xp = -hl - 0.02
        parts.box("pusher", (0.04, 2 * R, 2 * flat + 0.05), location=(xp, 0, 0.025), material="dark_metal")
        x_end = xb
        L_base = x_end - (xp - 0.02)
        parts.box("sled_base", (L_base, gauge + 0.1, 0.05), location=((x_end + xp - 0.02) / 2, 0, base_z - 0.025),
                  material="dark_metal")
        for k, (sx, sy) in enumerate([(0.0, 1), (0.0, -1), (x_end - 0.1, 1), (x_end - 0.1, -1)]):
            parts.box(f"shoe{k}", (0.14, 0.1, 0.05), location=(sx, sy * gauge / 2, base_z - 0.075), material="dark_metal")
        parts.box("armature", (L_base - 0.2, 0.3, 0.03), location=((x_end + xp - 0.02) / 2, 0, base_z - 0.065),
                  material="foil_silver")

    with parts.assembly("track"):
        for k, sy in enumerate((1, -1)):
            parts.box(f"rail{k}", (4.0, 0.08, 0.12), location=(0.5, sy * gauge / 2, base_z - 0.16), material="dark_metal")
        parts.box("stator", (4.0, 0.3, 0.04), location=(0.5, 0, base_z - 0.1), material="dark_metal")

    propulsion(d, R, flat, xc, xb, t, x0, rt)
    power(d, R, flat, xc, xb)
    comms(d, R, flat, xc, xb, t)
    attitude(d, R, flat, xc, xb, t)
    electronics(d, R, flat, xc, xb, t)


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
    # Two wings, shown deployed: a drive at each +-y corner, a yoke, then five panels along y, cells
    # (AZUR 3G30-Advanced 6x12, 60.7 x 124.5 mm) on the +z face, long side along x.
    xm = (xc + xb) / 2
    cw, cl, cg = 0.0607, 0.1245, 0.0015               # cell width, length, gap
    pw, pl, pt, gap = 0.46, 0.72, 0.02, 0.02          # panel across, along x, thick; gap between panels
    yoke = d["wing_yoke"]
    for sign, tag in ((1, "l"), (-1, "r")):
        with parts.assembly(f"solar_wing_{tag}"):
            y0 = sign * R                               # the corner
            parts.lathe(f"solar_drive_{tag}", [(0.0, 0.0), (0.05, 0.0), (0.05, 0.08), (0.0, 0.08)], segments=24,
                        location=(xm, y0 - sign * 0.01, 0), direction=(0, sign, 0), material="dark_metal")
            yd = y0 + sign * 0.07
            yi = y0 + sign * yoke                       # the wing's inner edge
            for k, dx in enumerate((-0.25, 0.25)):
                parts.strut(f"yoke_{tag}{k}", (xm, yd, 0), (xm + dx, yi, 0), radius=0.01, material="dark_metal")
            parts.strut(f"yoke_{tag}_bar", (xm - 0.27, yi, 0), (xm + 0.27, yi, 0), radius=0.01, material="dark_metal")
            cells = []
            for n in range(5):
                yc = sign * (abs(yi) + pw / 2 + n * (pw + gap))
                parts.box(f"panel_{tag}{n}", (pl, pw, pt), location=(xm, yc, 0), material="white_paint")
                for i in range(5):
                    for j in range(7):
                        cx = xm + (i - 2) * (cl + cg)
                        cy = yc + (j - 3) * (cw + cg)
                        cells.append(((cl, cw, 0.002), (cx, cy, pt / 2 + 0.001)))
            parts.boxes(f"cells_{tag}", cells, material="solar_cell")
            if sign == 1:
                parts.box("cell_ref", (cl, cw, 0.002), location=cells[17][1], material="solar_cell")

    # Two Saft VES16 8s4p batteries on the inside of the top and bottom side panels.
    with parts.assembly("batteries", internal=True):
        for k, sz in enumerate((1, -1)):
            parts.box(f"battery{k}", (0.308, 0.18, 0.09), location=(xm, 0, sz * (flat - 0.004 - 0.045)),
                      material="dark_metal")


def comms(d, R, flat, xc, xb, t):
    # S-band dish on the +z side, facing the Moon: a copy of Lunar Pathfinder's SANT. Only its
    # diameter is published; the depth, feed and pointing mechanism are estimates (spec).
    xm = (xc + xb) / 2
    rd = 0.43
    f = 0.35 * 2 * rd                                # focal length, f/D 0.35
    h_apm = 0.15
    z0 = flat + h_apm                                # the dish's vertex
    with parts.assembly("sband_antenna"):
        parts.lathe("apm_base", [(0.0, 0.0), (0.12, 0.0), (0.12, 0.06), (0.0, 0.06)], segments=32,
                    location=(xm, 0, flat), direction=(0, 0, 1), material="dark_metal")
        parts.lathe("apm_swashplates", [(0.0, 0.06), (0.1, 0.06), (0.1, 0.1), (0.09, 0.1), (0.09, 0.105),
                                        (0.1, 0.105), (0.1, h_apm), (0.0, h_apm)], segments=32,
                    location=(xm, 0, flat), direction=(0.0, math.sin(math.radians(4)), math.cos(math.radians(4))),
                    material="foil_silver")
        n = 16
        dish = [(rd * k / n, (rd * k / n) ** 2 / (4 * f)) for k in range(n + 1)]
        shell = dish + [(rd, dish[-1][1] - 0.008)] + [(r, z - 0.008) for r, z in reversed(dish[:-1])]
        parts.lathe("sband_reflector", shell, segments=64, location=(xm, 0, z0), direction=(0, 0, 1),
                    material="white_paint")
        # Backfire helix: a mast from the vertex to the focus, a helix cage and a small back reflector.
        parts.lathe("sband_feed", [(0.0, 0.0), (0.012, 0.0), (0.012, f - 0.2), (0.03, f - 0.2), (0.03, f - 0.01),
                                   (0.06, f - 0.01), (0.06, f), (0.0, f)], segments=24,
                    location=(xm, 0, z0), direction=(0, 0, 1), material="foil_gold")

    # X-band patch array on the forward deck, facing +x (the Earth).
    with parts.assembly("xband_antenna"):
        parts.box("xband_array", (0.00318, 0.0826, 0.098), location=(xb + 0.00159, 0.18, 0.12), material="white_paint")

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
            parts.lathe(f"star_tracker{k}", [(0.0, 0.0), (0.035, 0.0), (0.035, 0.055), (0.0495, 0.065),
                                             (0.0495, 0.12), (0.046, 0.12), (0.03, 0.07), (0.0, 0.07)],
                        segments=24, location=p, direction=n, material="black")

    # Bradford coarse sun sensors on +z and +x, the Mini fine sun sensor on +z.
    with parts.assembly("sun_sensors"):
        parts.box("css_top", (0.11, 0.11, 0.03), location=(xc + 0.08, 0, flat + 0.015), material="dark_metal")
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

