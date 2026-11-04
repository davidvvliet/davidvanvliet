# InvenSense MPU-6050 IMU. Built from lib/parts in metres; every number comes from
# specs/mpu6050.json (with its source) or is marked here as estimated.
# Frame: z up, package bottom at z = 0, centred in x and y; +X/+Y as the datasheet's
# orientation figure, pin 1 at the top left of the top view (-X, +Y).
import os
import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
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



def _mask(path):
    """A traced mask (white = silicon) as a bool array, row 0 at the top of the image."""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return (px.reshape(h, w, 4)[::-1, :, 0] > 0.5)


def _runs(row):
    """(start, end) of each run of True in a 1-D bool array."""
    e = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
    return list(zip(np.nonzero(e == 1)[0], np.nonzero(e == -1)[0]))


def traced(d, name, region, cell, z0, z1, m, mat, solid=None):
    """Silicon traced from the die photo: `m` marks, cell by cell (`cell` µm, row 0 at the
    photo's top), where the device layer is; it is extruded from z0 to z1 with the photo
    (material `mat`) on top. `solid`: all the silicon around it (default `m`); walls stand
    only where `m` meets a cell that isn't in it, so two parts that touch share no wall. Top faces
    are the mask merged into rectangles (runs per row, merged down); walls stand only where
    silicon meets a gap, each taking the photo's colour just inside the edge."""
    H, W = m.shape
    u0, v0, u1, v1 = region
    U = lambda j: u0 + j * cell
    V = lambda i: v0 + i * cell
    clamp = lambda t: min(1.0, max(0.0, t))
    uv = lambda u, v: (clamp((u - u0) / (u1 - u0)), clamp(1 - (v - v0) / (v1 - v0)))
    bm = bmesh.new()
    lay = bm.loops.layers.uv.new("UVMap")

    def quad(pts, uvs, want):
        vs = [bm.verts.new(p) for p in pts]
        n = (Vector(pts[1]) - Vector(pts[0])).cross(Vector(pts[2]) - Vector(pts[0]))
        if n.dot(Vector(want)) < 0:
            vs.reverse()
            uvs = list(reversed(uvs))
        face = bm.faces.new(vs)
        for loop, t in zip(face.loops, uvs):
            loop[lay].uv = t

    def P(u, v, z):
        x, y = die_xy(d, u, v)
        return (x, y, z)

    # Tops: rectangles from runs merged down the rows.
    open_ = {}
    for i in range(H + 1):
        runs = set(_runs(m[i])) if i < H else set()
        for r in [r for r in open_ if r not in runs]:
            a, b = r
            ua, ub, va, vb = U(a), U(b), V(open_.pop(r)), V(i)
            quad([P(ua, va, z1), P(ub, va, z1), P(ub, vb, z1), P(ua, vb, z1)],
                 [uv(ua, va), uv(ub, va), uv(ub, vb), uv(ua, vb)], (0, 0, 1))
        for r in runs:
            open_.setdefault(r, i)
    # Walls along rows (between row i-1 and row i) and along columns.
    pad = np.zeros((H + 2, W + 2), bool)
    pad[1:-1, 1:-1] = m
    full = np.zeros((H + 2, W + 2), bool)
    full[1:-1, 1:-1] = m if solid is None else solid
    for i in range(H + 1):
        above, below = pad[i, 1:-1], pad[i + 1, 1:-1]
        fa, fb = full[i, 1:-1], full[i + 1, 1:-1]
        for side, edge in ((1, above & ~fb), (-1, below & ~fa)):
            for a, b in _runs(edge):
                v = V(i)
                vi = v - side * cell / 2              # just inside the silicon
                t = uv(U((a + b) / 2), vi)
                pa, pb = P(U(a), v, z0), P(U(b), v, z0)
                n = (Vector(P(U(a), v + side, 0)) - Vector(P(U(a), v, 0)))
                quad([pa, pb, (pb[0], pb[1], z1), (pa[0], pa[1], z1)], [t] * 4, n)
    for j in range(W + 1):
        left, right = pad[1:-1, j], pad[1:-1, j + 1]
        fl, fr = full[1:-1, j], full[1:-1, j + 1]
        for side, edge in ((1, left & ~fr), (-1, right & ~fl)):
            for a, b in _runs(edge):
                u = U(j)
                ui = u - side * cell / 2
                t = uv(ui, V((a + b) / 2))
                pa, pb = P(u, V(a), z0), P(u, V(b), z0)
                n = (Vector(P(u + side, V(a), 0)) - Vector(P(u, V(a), 0)))
                quad([pa, pb, (pb[0], pb[1], z1), (pa[0], pa[1], z1)], [t] * 4, n)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-9)
    return parts._object(name, bm, mat, Matrix())


def device_layer(d, f, z):
    """The MEMS die's device layer, sensor by sensor, traced from the die photo (spec
    facts.die_trace): each sensor is its own assembly, clicked to focus."""
    T = f["die_trace"]["value"]
    folder = os.path.join(HARNESS, "refs", "mpu6050", "die")
    for key, region in T["regions"].items():
        m = _mask(os.path.join(folder, f"{key}-mask.png"))
        dim = _mask(os.path.join(folder, f"{key}-moving.png")) & m
        photo = bpy.data.images.load(os.path.join(folder, f"{key}.jpg"), check_existing=False)
        mat = materials.image(f"{key}_photo", photo, metallic=0.4, roughness=0.35)
        # The photo's dim silicon (the proof masses and what moves with them) and its bright
        # silicon (anchored frames and fixed combs) as separate parts of the sensor.
        with parts.assembly(key, internal=True):
            traced(d, f"{key}_frame", region, T["cell_um"], z["device_bottom"], z["device_top"], m & ~dim, mat, m)
            traced(d, f"{key}_masses", region, T["cell_um"], z["device_bottom"], z["device_top"], dim, mat, m)


def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    f = spec["facts"]
    package(d, f, spec)
    z = stack(d, f)
    pads = cmos(d, f, z)
    wires(d, f, z, pads)
    mems(d, f, z)
    device_layer(d, f, z)
