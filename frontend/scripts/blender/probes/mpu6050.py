# InvenSense MPU-6050 IMU. Built from lib/parts in metres; every number comes from
# specs/mpu6050.json (with its source) or is marked here as estimated.
# Frame: z up, package bottom at z = 0, centred in x and y; +X/+Y as the datasheet's
# orientation figure, pin 1 at the top left of the top view (-X, +Y).
import os
from lib import materials, parts, textures

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pin_positions(n, per_side, pitch, half):
    """Centre (x, y) and outward direction of pin n (1-based): 1-6 down the -X side, 7-12
    along -Y left to right, 13-18 up the +X side, 19-24 along +Y right to left (datasheet 7.1)."""
    side, k = divmod(n - 1, per_side)
    off = (k - (per_side - 1) / 2) * pitch
    if side == 0:
        return (-half, -off), (-1, 0)
    if side == 1:
        return (off, -half), (0, -1)
    if side == 2:
        return (half, off), (1, 0)
    return (-off, half), (0, 1)


def package(d, f, spec):
    """QFN-24: mould body, 24 leads flush with the sides and the exposed pad underneath (its
    pin 1 corner cut off), all 0.02 mm proud of the body's underside (A1), and the laser
    marking on top (pin 1 dot and lettering), traced from a photo."""
    Ld = f["leads"]["value"]
    X, Y, H = d["package_x"], d["package_y"], d["package_height"]
    t, a1 = Ld["frame_thickness"], Ld["standoff"]
    with parts.assembly("package", core=True):
        # 2 µm inside the sawn sides so the leads' cut ends show (design: real ends are flush).
        body = parts.box("package_body", (X - 4e-6, Y - 4e-6, H - a1), location=(0, 0, a1 + (H - a1) / 2),
                  material="mould_compound")
    with parts.assembly("leads"):
        for n in range(1, Ld["count"] + 1):
            (cx, cy), (ox, oy) = pin_positions(n, Ld["per_side"], Ld["pitch"], X / 2)
            c = (cx - ox * Ld["length"] / 2, cy - oy * Ld["length"] / 2, t / 2)
            size = (Ld["length"], Ld["width"], t) if ox else (Ld["width"], Ld["length"], t)
            parts.box(f"lead_{n}", size, location=c, material="foil_silver")
        # The pad's corner nearest pin 1 (-X, +Y) is cut off at 45 degrees (C0.3).
        px, py, c = d["exposed_pad_x"], d["exposed_pad_y"], f["exposed_pad_chamfer"]["value"]
        parts.outline_plate("exposed_pad", [(0, 0), (1, 0), (1, 1), (c / px, 1), (0, 1 - c / py)],
                            px, py, t, location=(0, 0, 0), direction=(0, 0, 1), up=(0, 1, 0),
                            material="foil_silver")
    # The laser marking covers the whole top, image top towards +Y (pin 1's row).
    img = textures.marking("mpu6050_marking", [(os.path.join(HARNESS, "refs", "mpu6050", "marking-mask.png"),
                                               materials.colour(spec["materials"]["laser_marking"]))],
                           os.path.join(HARNESS, "out", "mpu6050", "textures"))
    mat = materials.image("mpu6050_marking", img, metallic=0.0, roughness=0.9, cutout=True)
    with parts.assembly("marking"):
        parts.decal("marking", body, center=(0, 0, H), direction=(0, 0, -1), up=(0, 1, 0),
                    width=X - 4e-6, height=Y - 4e-6, material=mat, step=0.0005, lift=1e-6)


def stack(d, f):
    """Heights of the layers, bottom up (spec facts.thicknesses, estimated)."""
    T = f["thicknesses"]["value"]
    z = {"frame_top": f["leads"]["value"]["frame_thickness"]}
    z["cmos_bottom"] = z["frame_top"] + T["die_attach"]
    z["cmos_top"] = z["cmos_bottom"] + T["cmos_die"]
    z["device_bottom"] = z["cmos_top"] + T["bond_gap"]
    z["device_top"] = z["device_bottom"] + f["mems_device_layer"]["value"]
    z["handle_top"] = z["device_top"] + T["handle_wafer"]
    return z


def die_xy(d, u, v):
    """A point on the MEMS die photo (µm, x right, y down from its top left corner) in the
    model: the die lies face down, so the photo is mirrored across X; its 2778 µm side runs
    along X, the same direction as the sensors' X axis (spec facts.mems_layout_um)."""
    W, H = d["mems_die_x"] * 1e6, d["mems_die_y"] * 1e6
    return (-(u - W / 2) * 1e-6, (H / 2 - v) * 1e-6)


def die_rect(d, r):
    """[u0, v0, u1, v1] on the die photo as a model rectangle: centre (x, y) and size (w, h)."""
    (x0, y0), (x1, y1) = die_xy(d, r[0], r[1]), die_xy(d, r[2], r[3])
    return ((x0 + x1) / 2, (y0 + y1) / 2), (abs(x1 - x0), abs(y1 - y0))


def cmos(d, f, z):
    """The CMOS chip on the exposed pad: the die, the aluminium electrodes under the MEMS
    plates, and the bond pads in strips along its two Y edges."""
    lay = f["mems_layout_um"]["value"]
    E = f["electrodes"]["value"]
    B = f["bond_wires"]["value"]
    with parts.assembly("cmos_die", internal=True):
        parts.box("cmos_die", (d["cmos_die_x"], d["cmos_die_y"], z["cmos_top"] - z["cmos_bottom"]),
                  location=(0, 0, (z["cmos_bottom"] + z["cmos_top"]) / 2), material="cmos_surface")
        items = []
        for key in ("gyro_x", "gyro_y", "gyro_z"):
            for r in lay[key]["plates"]:
                (cx, cy), (w, h) = die_rect(d, r)
                items.append(((w - 2 * E["inset"], h - 2 * E["inset"], E["thickness"]),
                              (cx, cy, z["cmos_top"] + E["thickness"] / 2)))
        parts.boxes("electrodes", items, material="cmos_aluminium")
    pads = {}
    Ld = f["leads"]["value"]
    with parts.assembly("bond_pads", internal=True):
        ys = d["cmos_die_y"] / 2 - B["pad_strip"] / 2
        for sign, pins in ((-1, [6, 7, 8, 9, 10, 11, 12, 13]), (1, [18, 19, 20, 21, 22, 23, 24, 1])):
            ends = sorted(pins, key=lambda n: pin_positions(n, Ld["per_side"], Ld["pitch"], d["package_x"] / 2)[0][0])
            span = d["cmos_die_x"] - 2 * B["pad_strip"]
            items = []
            for i, n in enumerate(ends):
                x = -span / 2 + span * (i + 0.5) / len(ends)
                pads[n] = (x, sign * ys, z["cmos_top"])
                items.append(((B["pad_size"], B["pad_size"], E["thickness"]), (x, sign * ys, z["cmos_top"] + E["thickness"] / 2)))
            parts.boxes(f"bond_pads_{'my' if sign < 0 else 'py'}", items, material="cmos_aluminium")
    return pads


def wires(d, f, z, pads):
    """Gold wires from each bonded pin's CMOS pad up in a loop and down onto its lead."""
    Ld = f["leads"]["value"]
    B = f["bond_wires"]["value"]
    with parts.assembly("bond_wires", internal=True):
        for n in f["bonded_pins"]["value"]:
            (cx, cy), (ox, oy) = pin_positions(n, Ld["per_side"], Ld["pitch"], d["package_x"] / 2)
            # The wire lands on the lead's inner end, 0.1 mm in from its tip (estimated).
            lx, ly = cx - ox * (Ld["length"] - 0.0001), cy - oy * (Ld["length"] - 0.0001)
            px, py, pz = pads[n]
            top = pz + B["loop_height"]
            pts = [(px, py, pz), (px, py, top), (px + (lx - px) * 0.3, py + (ly - py) * 0.3, top),
                   (lx, ly, z["frame_top"])]
            parts.tube(f"wire_{n}", pts, radius=B["diameter"] / 2, segments=6,
                       bend_radius=B["loop_height"] * 0.45, material="foil_gold")


def mems(d, f, z):
    """The MEMS chip face down on the CMOS chip: the handle wafer on top, its lid (with the
    package, so the inside view looks straight in), and in the device layer the seal ring that
    bonds it to the CMOS chip and seals the cavity."""
    lay = f["mems_layout_um"]["value"]
    sr = lay["seal_ring"]
    W, H = d["mems_die_x"], d["mems_die_y"]
    with parts.assembly("mems_lid"):
        parts.box("mems_handle", (W, H, z["handle_top"] - z["device_top"]),
                  location=(0, 0, (z["device_top"] + z["handle_top"]) / 2), material="silicon")
    with parts.assembly("mems_die", internal=True):
        (cx, cy), (w, h) = die_rect(d, [sr["x"][0], sr["y"][0], sr["x"][1], sr["y"][1]])
        t = sr["width"] * 1e-6
        dz = z["device_top"] - z["cmos_top"]
        zc = (z["cmos_top"] + z["device_top"]) / 2
        parts.boxes("seal_ring", [((w, t, dz), (cx, cy + s * (h - t) / 2, zc)) for s in (1, -1)] +
                    [((t, h - 2 * t, dz), (cx + s * (w - t) / 2, cy, zc)) for s in (1, -1)],
                    material="silicon")


class Layer:
    """Boxes in the MEMS device layer, in model metres. Moving parts float a bond gap above
    the CMOS chip; anchors reach down to it (they are what holds the structure)."""

    def __init__(self, z):
        self.z = z
        self.items, self.fixed = [], []

    def add(self, cx, cy, w, h):
        zb, zt = self.z["device_bottom"], self.z["device_top"]
        self.items.append(((w, h, zt - zb), (cx, cy, (zb + zt) / 2)))

    def anchor(self, cx, cy, w, h):
        zb, zt = self.z["cmos_top"], self.z["device_top"]
        self.fixed.append(((w, h, zt - zb), (cx, cy, (zb + zt) / 2)))

    def frame(self, cx, cy, w, h, t):
        """A rectangular ring of width t."""
        self.add(cx, cy + (h - t) / 2, w, t)
        self.add(cx, cy - (h - t) / 2, w, t)
        self.add(cx - (w - t) / 2, cy, t, h - 2 * t)
        self.add(cx + (w - t) / 2, cy, t, h - 2 * t)

    def comb(self, cx, cy, w, h, along, finger, gap):
        """Interdigitated comb bank in the rectangle: two spines on opposite sides with fingers
        reaching from each in turn (one side moves with the mass, the other is fixed). `along`:
        the direction the fingers run, "x" or "y"."""
        spine = finger * 1.5
        pitch = finger + gap
        if along == "x":
            self.add(cx - (w - spine) / 2, cy, spine, h)
            self.add(cx + (w - spine) / 2, cy, spine, h)
            n = int((h - finger) // pitch)
            length = (w - 2 * spine) * 0.85
            for i in range(n):
                y = cy - (n - 1) * pitch / 2 + i * pitch
                side = -1 if i % 2 else 1
                self.add(cx + side * ((w - 2 * spine) - length) / 2, y, length, finger)
        else:
            self.add(cx, cy - (h - spine) / 2, w, spine)
            self.add(cx, cy + (h - spine) / 2, w, spine)
            n = int((w - finger) // pitch)
            length = (h - 2 * spine) * 0.85
            for i in range(n):
                x = cx - (n - 1) * pitch / 2 + i * pitch
                side = -1 if i % 2 else 1
                self.add(x, cy + side * ((h - 2 * spine) - length) / 2, finger, length)

    def emit(self, name):
        parts.boxes(name, self.items, material="mems_structure")
        if self.fixed:
            parts.boxes(f"{name}_anchors", self.fixed, material="silicon")


def gyros(d, f, z):
    """Three vibrating gyroscopes (top row of the die): their drive masses (the plates), the
    sense frame round them, comb banks above and below, and the anchors and springs holding
    each frame. Left to right on the die: Z, Y, X (nasiri2010 Fig. 7)."""
    lay = f["mems_layout_um"]["value"]
    C = f["comb_fingers"]["value"]
    s = 1e-6
    for key in ("gyro_x", "gyro_y", "gyro_z"):
        g = lay[key]
        L = Layer(z)
        plates = [die_rect(d, r) for r in g["plates"]]
        for (cx, cy), (w, h) in plates:
            L.add(cx, cy, w, h)
        # Sense frame: a ring 12 µm wide, 25 µm round the plates (representative).
        xs = [c[0] + sgn * sz[0] / 2 for c, sz in plates for sgn in (-1, 1)]
        ys = [c[1] + sgn * sz[1] / 2 for c, sz in plates for sgn in (-1, 1)]
        fw, fh = max(xs) - min(xs) + 50 * s, max(ys) - min(ys) + 50 * s
        fx, fy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        L.frame(fx, fy, fw, fh, 12 * s)
        # Each plate hangs from the frame on two torsion beams across its middle (6 µm wide).
        for (cx, cy), (w, h) in plates:
            if w >= h:
                L.add(cx - w / 2 - 12.5 * s, cy, 25 * s, 6 * s)
                L.add(cx + w / 2 + 12.5 * s, cy, 25 * s, 6 * s)
            else:
                L.add(cx, cy - h / 2 - 12.5 * s, 6 * s, 25 * s)
                L.add(cx, cy + h / 2 + 12.5 * s, 6 * s, 25 * s)
        for r in g["combs"]:
            (cx, cy), (w, h) = die_rect(d, r)
            L.comb(cx, cy, w, h, "x" if g["fingers"] == "horizontal" else "y",
                   C["modelled_width"], C["modelled_gap"])
        # Anchors: one above and one below the frame, at its centre line, each tied to the
        # frame by a spring beam (representative of the die's centre-column anchors).
        for sgn in (1, -1):
            ay = fy + sgn * (fh / 2 + 40 * s)
            L.anchor(fx, ay, 40 * s, 40 * s)
            L.add(fx, fy + sgn * (fh / 2 + 10 * s), 6 * s, 20 * s)
        with parts.assembly(key, internal=True):
            L.emit(key)


def accelerometers(d, f, z):
    """Three accelerometers (bottom row). X and Y: proof masses in two cells, each with a
    window holding an anchor and comb banks either side of it along the axis of motion,
    hung on long folded springs that bend only along that axis. Z: two teeter-totter paddles,
    each on a torsion beam across its centre, with an electrode under each half."""
    lay = f["mems_layout_um"]["value"]
    C = f["comb_fingers"]["value"]
    s = 1e-6
    for key in ("accel_x", "accel_y"):
        a = lay[key]
        mx = a["motion"] == "x"
        L = Layer(z)
        for r in a["cells"]:
            (cx, cy), (w, h) = die_rect(d, r)
            # Mass: the cell with a window 70% of its size (representative).
            ww, wh = w * 0.7, h * 0.7
            L.frame(cx, cy, w, h, min(w - ww, h - wh) / 2)
            L.anchor(cx, cy, ww * 0.18, wh * 0.18)
            # Combs between the anchor and the mass on both sides along the motion; their
            # fingers run across the motion, so the gaps close as the mass moves.
            for sgn in (1, -1):
                if mx:
                    L.comb(cx + sgn * ww * 0.3, cy, ww * 0.3, wh * 0.85, "y", C["modelled_width"], C["modelled_gap"])
                else:
                    L.comb(cx, cy + sgn * wh * 0.3, ww * 0.85, wh * 0.3, "x", C["modelled_width"], C["modelled_gap"])
        for r in a["springs"]:
            (cx, cy), (w, h) = die_rect(d, r)
            # A folded spring: two long beams 6 µm wide joined at both ends, anchored mid-way.
            if mx:
                for sgn in (1, -1):
                    L.add(cx + sgn * w / 4, cy, 6 * s, h)
                L.add(cx, cy + h / 2 - 3 * s, w / 2 + 6 * s, 6 * s)
                L.add(cx, cy - h / 2 + 3 * s, w / 2 + 6 * s, 6 * s)
                L.anchor(cx, cy, w * 0.35, 40 * s)
            else:
                for sgn in (1, -1):
                    L.add(cx, cy + sgn * h / 4, w, 6 * s)
                L.add(cx + w / 2 - 3 * s, cy, 6 * s, h / 2 + 6 * s)
                L.add(cx - w / 2 + 3 * s, cy, 6 * s, h / 2 + 6 * s)
                L.anchor(cx, cy, 40 * s, h * 0.35)
        with parts.assembly(key, internal=True):
            L.emit(key)
    a = lay["accel_z"]
    L = Layer(z)
    pads = []
    for r, c in zip(a["paddles"], a["centres"]):
        (cx, cy), (w, h) = die_rect(d, r)
        (ix, iy), (iw, ih) = die_rect(d, c)
        by = die_xy(d, 0, a["beam_v"])[1]
        # Paddle: the plate round its centre opening, heavier on one side (its -Y half is
        # solid, its +Y half has a cut-out), so it tips under acceleration along Z.
        t = (h - ih) / 2
        L.add(cx, cy - (h - t) / 2, w, t)
        L.add(cx - (w + iw) / 4, cy, (w - iw) / 2, ih)
        L.add(cx + (w + iw) / 4, cy, (w - iw) / 2, ih)
        L.add(cx - w * 0.35, cy + (h - t) / 2, w * 0.3, t)
        L.add(cx + w * 0.35, cy + (h - t) / 2, w * 0.3, t)
        # Torsion beam across the opening, anchored at its middle.
        L.add(ix, by, iw, 8 * s)
        L.anchor(ix, by, 40 * s, 40 * s)
        pads += [(cx, cy + sgn * h / 4, w * 0.8, h * 0.35) for sgn in (1, -1)]
    with parts.assembly("accel_z", internal=True):
        L.emit("accel_z")
    E = f["electrodes"]["value"]
    with parts.assembly("cmos_die", internal=True):
        parts.boxes("electrodes_accel_z", [((w, h, E["thickness"]), (x, y, z["cmos_top"] + E["thickness"] / 2))
                                           for x, y, w, h in pads], material="cmos_aluminium")


def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    f = spec["facts"]
    package(d, f, spec)
    z = stack(d, f)
    pads = cmos(d, f, z)
    wires(d, f, z, pads)
    mems(d, f, z)
    gyros(d, f, z)
    accelerometers(d, f, z)
