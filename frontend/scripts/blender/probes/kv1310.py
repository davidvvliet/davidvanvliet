# Sony KV-1310 Trinitron (1968). Built from lib/parts in metres; every number comes from
# specs/kv1310.json (with its source) or is marked here as estimated.
# Frame: z up, feet on z = 0, centred in x; the screen faces -y (the viewer's front), so the
# viewer's left is -x: the screen sits on -x, the control column on +x.
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import materials, parts, textures, tiling

SPEC = [None]
ANIM = {}
HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(HERE, "..", "refs", "kv1310", "labels")
TEX = os.path.join(HERE, "..", "out", "kv1310", "textures")


# --- shape helpers ------------------------------------------------------------------------

def _solid(name, verts, faces, material):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    return parts._object(name, bm, material, Matrix(), None)


def rrect(w, h, r, n=5):
    """Rounded rectangle (u, v) points, counter-clockwise, centred; 4 * (n + 1) points."""
    pts = []
    for cu, cv, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def ring(name, outer, inner, cx, cz, y_front, y_back, material, inner_back=None):
    """A frame facing -y: outer and inner outlines (same point count) from y_front back to
    y_back; the hole's wall runs back to `inner_back` (default y_back)."""
    n = len(outer)
    ib = y_back if inner_back is None else inner_back
    P = lambda uv, y: (cx + uv[0], y, cz + uv[1])
    verts = [P(p, y_front) for p in outer] + [P(p, y_front) for p in inner] + \
            [P(p, y_back) for p in outer] + [P(p, ib) for p in inner]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces += [(i, j, n + j, n + i), (2 * n + i, 2 * n + j, j, i),
                  (n + i, n + j, 3 * n + j, 3 * n + i), (3 * n + i, 3 * n + j, 2 * n + j, 2 * n + i)]
    return _solid(name, verts, faces, material)


def plate(name, outline, cx, cz, y_front, y_back, material):
    """A solid from a front outline [(u, v)] (u along x, v along z), y_front..y_back."""
    n = len(outline)
    verts = [(cx + u, y_front, cz + v) for u, v in outline] + [(cx + u, y_back, cz + v) for u, v in outline]
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return _solid(name, verts, faces, material)


def cyl_y(name, r, x, z, y_front, y_back, material, segments=32):
    """A cylinder along y from y_front back to y_back."""
    return parts.cylinder(name, r, y_back - y_front, location=(x, y_front, z), direction=(0, 1, 0),
                          segments=segments, material=material)


# --- the front, from the rectified photo (mm from the front's top-left, u right, v down) ---

class Front:
    def __init__(self, spec):
        P = spec["from_photos"]
        E = {k: v["value"] for k, v in spec["estimates"].items()}
        D = {k: v["value"] for k, v in spec["dimensions"].items()}
        self.L = P["layout"]["value"]
        self.W = D["cabinet_width"]
        self.H = P["front_height"]["value"] / 1000
        self.feet = E["feet"]
        self.depth = D["cabinet_depth"]
        # Knobs stand ~10 mm ahead of the wood's front edge (photo); the overall depth runs
        # from the knobs' fronts to the back cover (spec cabinet_depth).
        self.y_front = -self.depth / 2 + 0.010
        self.wall, self.recess = E["wall"], E["panel_recess"]
        self.sleeve_back = self.y_front + E["sleeve_depth"]

    def x(self, u):
        return -self.W / 2 + u / 1000

    def z(self, v):
        return self.feet + self.H - v / 1000

    def box(self, r):
        """(cx, cz, w, h) of a [u0, v0, u1, v1] rectangle."""
        u0, v0, u1, v1 = r
        return self.x((u0 + u1) / 2), self.z((v0 + v1) / 2), (u1 - u0) / 1000, (v1 - v0) / 1000


def cabinet(F):
    """The walnut sleeve: top, bottom and sides, open at the back (estimated from the KV-1320UB),
    on four small feet."""
    W, H, t, z0 = F.W, F.H, F.wall, F.feet
    y0, y1 = F.y_front, F.sleeve_back
    d, yc = y1 - y0, (y0 + y1) / 2
    with parts.assembly("cabinet", core=True):
        parts.box("sleeve_top", (W, d, t), location=(0, yc, z0 + H - t / 2), material="walnut")
        parts.box("sleeve_bottom", (W, d, t), location=(0, yc, z0 + t / 2), material="walnut")
        for s in (-1, 1):
            parts.box(f"sleeve_{'left' if s < 0 else 'right'}", (t, d, H - 2 * t),
                      location=(s * (W / 2 - t / 2), yc, z0 + H / 2), material="walnut")
    with parts.assembly("feet"):
        for sx in (-1, 1):
            for sy, yy in (("front", y0 + 0.03), ("back", y1 - 0.03)):
                parts.box(f"foot_{sy}_{'l' if sx < 0 else 'r'}", (0.03, 0.02, z0),
                          location=(sx * (W / 2 - 0.035), yy, z0 / 2), material="knob_black")


def front_panel(F):
    L = F.L
    yf = F.y_front
    tw = L["trim_width"] / 1000
    cx, cz, w, h = F.box(L["trim_outer"])
    with parts.assembly("trim"):
        # Silver frame inside the wood's front edge, 2 mm back from it.
        ring("trim", rrect(w, h, 0.002), rrect(w - 2 * tw, h - 2 * tw, 0.001),
             cx, cz, yf + 0.002, yf + 0.012, "trim_silver")
    ip = F.recess
    bx, bz, bw, bh = F.box(L["bezel"])
    with parts.assembly("front_panel"):
        # Black panel behind the trim, with the bezel's opening.
        outer = rrect(w - 2 * tw, h - 2 * tw, 0.001)
        inner = [(u + bx - cx, v + bz - cz) for u, v in rrect(bw, bh, 0.003)]
        ring("front_panel", outer, inner, cx, cz, yf + ip, yf + ip + 0.004, "panel_black")
    sx, sz, sw, sh = F.box(L["screen_opening"])
    r = L["screen_corner_r"] / 1000
    with parts.assembly("bezel"):
        # Stands 4 mm forward of the panel; its inner wall slopes back towards the glass.
        outer = rrect(bw, bh, 0.003)
        inner = [(u + sx - bx, v + sz - bz) for u, v in rrect(sw, sh, r)]
        ring("bezel", outer, inner, bx, bz, yf + ip - 0.004, yf + ip + 0.004, "bezel_black",
             inner_back=yf + ip + 0.008)
        ring("bezel_edge", rrect(bw, bh, 0.003), rrect(bw - 0.003, bh - 0.003, 0.002),
             bx, bz, yf + ip - 0.0045, yf + ip - 0.0035, "trim_silver")
        px, pz, pw, ph = F.box(L["sony_plate"])
        parts.box("sony_plate", (pw, 0.0015, ph), location=(px, yf + ip - 0.0047, pz), material="bezel_black")
    with parts.assembly("control_column"):
        cxx, czz, cw, ch = F.box(L["column"])
        parts.box("column", (cw, 0.004, ch), location=(cxx, yf + ip - 0.002, czz), material="bezel_black")
        for nm, key, mat in (("speaker", "speaker", "speaker_grille"), ("badge", "badge", "bezel_black"),
                             ("control_plate", "control_plate", "control_plate")):
            qx, qz, qw, qh = F.box(L[key])
            parts.box(nm, (qw, 0.002, qh), location=(qx, yf + ip - 0.005, qz), material=mat)
        qx, qz, qw, qh = F.box(L["color_plate"])
        parts.box("color_plate", (qw, 0.001, qh), location=(qx, yf + ip - 0.0065, qz), material="bezel_black")
    with parts.assembly("channel_dial"):
        du, dv = L["dial_centre"]
        x, z, R = F.x(du), F.z(dv), L["dial_r"] / 1000
        y = yf + ip - 0.006
        cyl_y("dial_ring", R, x, z, y - 0.004, y, "trim_silver", 48)
        cyl_y("dial_face", R * 0.86, x, z, y - 0.006, y - 0.004, "knob_black", 48)
        cyl_y("dial_hub", R * 0.42, x, z, y - 0.012, y - 0.006, "trim_silver", 32)
        # The grip bar across the hub, turned as in the photo (about 30 degrees off upright).
        grip = parts.box("dial_grip", (0.005, 0.010, R * 1.5), location=(x, y - 0.011, z),
                         material="control_plate")
        grip.rotation_euler = (0, math.radians(-30), 0)
    with parts.assembly("knobs"):
        kv = L["knob_v"]
        kr = L["knob_d"] / 2000
        y = yf + ip
        caps = ["knob_red", "knob_red", "knob_black", "knob_black"]
        for i, (u, cap) in enumerate(zip(L["knobs_u"], caps)):
            x, z = F.x(u), F.z(kv)
            cyl_y(f"knob_{i + 1}_collar", kr * 0.7, x, z, y - 0.008, y, "trim_silver", 24)
            cyl_y(f"knob_{i + 1}", kr, x, z, y - 0.018, y - 0.008, cap, 32)
        pu, pv = L["power_knob"]
        x, z = F.x(pu), F.z(pv)
        cyl_y("power_knob_collar", kr * 0.7, x, z, y - 0.008, y, "trim_silver", 24)
        cyl_y("power_knob", kr, x, z, y - 0.018, y - 0.008, "knob_red", 32)
        for i, (ju, jv) in enumerate(L["jacks"]):
            cyl_y(f"jack_{i + 1}", 0.0032, F.x(ju), F.z(jv), y - 0.002, y, "trim_silver", 20)


def screen(F):
    """The tube's faceplate as seen through the bezel: cylindrical, straight top to bottom and
    bowed side to side (ohkoshi_1973). Its radius is estimated."""
    L = F.L
    sx, sz, sw, sh = F.box(L["screen_opening"])
    w, h = sw + 0.016, sh + 0.016
    R = 0.55  # horizontal radius of the face, estimated
    yc = F.y_front + F.recess + 0.004   # the face's front at its centre, just behind the bezel
    n = 24
    with parts.assembly("screen", inside=True):
        verts = []
        for dy in (0.0, 0.010):
            for i in range(n + 1):
                u = -w / 2 + w * i / n
                sag = R - math.sqrt(R * R - u * u)
                for zz in (sz - h / 2, sz + h / 2):
                    verts.append((sx + u, yc + sag + dy, zz))

        def V(t, i, top):
            return t * (n + 1) * 2 + i * 2 + top
        faces = []
        for i in range(n):
            faces.append((V(0, i, 0), V(0, i, 1), V(0, i + 1, 1), V(0, i + 1, 0)))
            faces.append((V(1, i, 0), V(1, i + 1, 0), V(1, i + 1, 1), V(1, i, 1)))
            faces.append((V(0, i, 1), V(1, i, 1), V(1, i + 1, 1), V(0, i + 1, 1)))
            faces.append((V(0, i, 0), V(0, i + 1, 0), V(1, i + 1, 0), V(1, i, 0)))
        faces.append((V(0, 0, 0), V(1, 0, 0), V(1, 0, 1), V(0, 0, 1)))
        faces.append((V(0, n, 0), V(0, n, 1), V(1, n, 1), V(1, n, 0)))
        _solid("faceplate", verts, faces, "screen_glass")


def handle(F, spec):
    """Black carry handle with a silver top strip; posts about a third of the way back."""
    P = spec["from_photos"]["handle"]["value"]
    hh = spec["estimates"]["handle_height"]["value"]
    L = P["length"] / 1000
    top = F.feet + F.H
    y = F.y_front + P["from_front"] * (F.sleeve_back - F.y_front)
    with parts.assembly("handle"):
        parts.box("handle_bar", (L, 0.020, 0.012), location=(0, y, top + hh - 0.009), material="knob_black")
        parts.box("handle_strip", (L - 0.006, 0.014, 0.003), location=(0, y, top + hh - 0.0015),
                  material="trim_silver")
        for s in (-1, 1):
            parts.box(f"handle_post_{'l' if s < 0 else 'r'}", (0.022, 0.016, hh - 0.012),
                      location=(s * (L / 2 - 0.016), y, top + (hh - 0.012) / 2), material="knob_black")


def back_cover(F):
    """Black plastic back: a plate filling the sleeve's back opening, standing out behind it,
    and a raised hood over the tube's neck (estimated from the KV-1320UB's back)."""
    W, H, t, z0 = F.W, F.H, F.wall, F.feet
    yb = F.sleeve_back
    back = F.depth / 2
    with parts.assembly("back_cover"):
        iw, ih = W - 2 * t - 0.002, H - 2 * t - 0.002
        parts.box("back_panel", (iw, 0.050, ih), location=(0, yb - 0.010, z0 + H / 2), material="back_plastic")
        sx, sz, _, _ = F.box(F.L["screen_opening"])
        plate("neck_hood", rrect(0.20, 0.15, 0.025), sx, sz, yb + 0.014, back, "back_plastic")
        back_detail(F, iw, ih, yb + 0.015, sx, sz, 0.20, 0.15, back)


def boxes(name, rects, y0, y1, material):
    """Several boxes in one mesh: rects [(x0, z0, x1, z1)], from y0 back to y1."""
    verts, faces = [], []
    for x0, z0, x1, z1 in rects:
        k = len(verts)
        verts += [(x, y, z) for y in (y0, y1) for z in (z0, z1) for x in (x0, x1)]
        faces += [(k + a, k + b, k + c, k + d) for a, b, c, d in
                  ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))]
    return _solid(name, verts, faces, material)


def back_detail(F, cw, ch, yf, hx, hz, hw, hh, yh):
    """Vents, aerial panel, switch, power socket and nameplate on the back cover, laid out as
    fractions of the KV-1320UB's cover (spec from_photos.back_layout). Seen from behind, the
    photo's left is +x."""
    B = SPEC[0]["from_photos"]["back_layout"]["value"]
    cz = F.feet + F.H / 2
    X = lambda u: (0.5 - u) * cw
    Z = lambda v: cz + (0.5 - v) * ch
    R = lambda r: (X(r[2]), Z(r[3]), X(r[0]), Z(r[1]))           # [u0, v0, u1, v1] -> x0, z0, x1, z1
    pitch = B["slot_pitch"] * cw
    def slots(r, xf, zf, w, h):
        u0, v0, u1, v1 = r
        n = int((u1 - u0) * w / pitch)
        out = []
        for i in range(n):
            u = u0 + (i + 0.5) * (u1 - u0) / n
            x = xf(u)
            out.append((x - pitch * B["slot_fill"] / 2, zf(v1), x + pitch * B["slot_fill"] / 2, zf(v0)))
        return out
    p = 0.0004                                                    # paint-thin, just behind the face
    boxes("back_vents", slots(B["top_vents"], X, Z, cw, ch) + slots(B["bottom_vents"], X, Z, cw, ch),
          yf - p, yf + p, "vent_shadow")
    HX = lambda u: hx + (0.5 - u) * hw
    HZ = lambda v: hz + (0.5 - v) * hh
    boxes("hood_vents", sum((slots(r, HX, HZ, hw, hh) for r in B["hood_vents"]), []), yh - p, yh + p, "vent_shadow")
    bu, bv, bs = B["hood_badge"]
    cyl_y("hood_badge", bs * hw / 2, HX(bu), HZ(bv), yh - 0.001, yh + 0.0012, "back_plastic", segments=24)
    x0, z0, x1, z1 = R(B["aerial_panel"])
    boxes("aerial_panel", [(x0, z0, x1, z1)], yf - 0.001, yf + 0.002, "back_plastic")
    su, sv, ss = B["aerial_socket"]
    cyl_y("aerial_socket", ss * cw / 2, X(su), Z(sv), yf + 0.001, yf + 0.008, "aerial_socket", segments=16)
    x0, z0, x1, z1 = R(B["switch"])
    boxes("slide_switch", [(x0, z0, x1, z1)], yf - 0.001, yf + 0.003, "back_knob")
    ru, rv, rs = B["red_button"]
    cyl_y("red_button", rs * cw / 2, X(ru), Z(rv), yf - 0.001, yf + 0.004, "button_red", segments=12)
    x0, z0, x1, z1 = R(B["power_socket"])
    boxes("power_socket", [(x0, z0, x1, z1)], yf - 0.001, yf + 0.006, "back_knob")
    x0, z0, x1, z1 = R(B["nameplate"])
    boxes("nameplate", [(x0, z0, x1, z1)], yf - 0.0003, yf + 0.0006, "nameplate_brass")


# --- the picture tube (Internal view) -------------------------------------------------------

def glow(key, emission=0.0):
    """A see-through version of spec material `key` (its "alpha"), optionally glowing."""
    import bpy
    e = SPEC[0]["materials"][key]
    col = materials.colour(e)
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Metallic"].default_value = e.get("metallic", 0.0)
    bsdf.inputs["Roughness"].default_value = e.get("roughness", 0.5)
    bsdf.inputs["Alpha"].default_value = e.get("alpha", 1.0)
    bsdf.inputs["Emission Color"].default_value = (*col, 1.0)
    bsdf.inputs["Emission Strength"].default_value = emission
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    mat.diffuse_color = (*col, e.get("alpha", 1.0))
    return mat


def superellipse(a, b, p, n=40):
    """(u, v) points of |u/a|^p + |v/b|^p = 1, counter-clockwise."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2 / p), c), b * math.copysign(abs(s) ** (2 / p), s)))
    return pts


def loft_y(name, rings, cx, cz, material, cap_front=False, cap_back=False):
    """A skin through rings [(y, [(u, v), ...]), ...] (same point count), along +y."""
    n = len(rings[0][1])
    verts = [(cx + u, y, cz + v) for y, pts in rings for u, v in pts]
    faces = []
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    if cap_front:
        faces.append(list(range(n - 1, -1, -1)))
    if cap_back:
        last = (len(rings) - 1) * n
        faces.append([last + i for i in range(n)])
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = parts._object(name, bm, material, Matrix(), None)
    obj.data.shade_smooth()
    return obj


def curved_sheet(name, sx, sz, w, h, y0, R, material, n=32, uv=None):
    """A thin sheet bowed like the face (radius R about a vertical axis), its centre at y0;
    `uv`: (repeat_w, repeat_h) metres per texture tile, u along x."""
    bm = bmesh.new()
    lay = bm.loops.layers.uv.new("UVMap") if uv else None
    rows = []
    for i in range(n + 1):
        u = -w / 2 + w * i / n
        y = y0 + R - math.sqrt(R * R - u * u)
        rows.append([bm.verts.new((sx + u, y, sz - h / 2)), bm.verts.new((sx + u, y, sz + h / 2))])
    for i in range(n):
        f = bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
        if f.normal.y > 0:
            f.normal_flip()
        if lay:
            for loop in f.loops:
                p = loop.vert.co
                loop[lay].uv = ((p.x - sx + w / 2) / uv[0], (p.z - sz + h / 2) / uv[1])
    return parts._object(name, bm, material, Matrix(), None)


def stripes_material(name, pitch, colours, slit=None, px=96):
    """A repeating tile of vertical stripes (one triad of colours per `pitch`), or, with
    `slit` (the open share), a grille: steel with transparent slits."""
    k = 4
    w = px
    rep = pitch * k
    x = (np.arange(w) + 0.5) / w * k % 1.0      # position within one pitch
    if slit is None:
        idx = np.minimum((x * len(colours)).astype(int), len(colours) - 1)
        row = np.array([tiling.srgb(colours[i]) for i in idx], np.float32)
        img = np.repeat(row[None], 8, 0)
        base = tiling.image("kv1310", f"{name}_base", img, "sRGB")
        return materials.image(name, base, metallic=0.0, roughness=0.6), rep
    e = SPEC[0]["materials"]["grille_steel"]
    a = (np.abs(x - 0.5) > slit / 2).astype(np.float32)
    rgb = np.repeat(np.repeat(np.array(materials.colour(e), np.float32)[None, None], 8, 0), w, 1)
    img = textures._save(f"{name}_base", rgb, TEX, "sRGB", alpha=np.repeat(a[None], 8, 0))
    img["tiling"] = True
    return materials.image(name, img, metallic=1.0, roughness=e["roughness"], cutout=True), rep


def picture_tube(spec, F):
    T = spec["estimates"]["tube"]["value"]
    G = spec["facts"]["aperture_grille"]["value"]
    sx, sz, sw, sh = F.box(F.L["screen_opening"])
    y_face = F.y_front + F.recess + 0.004
    y_in = y_face + 0.010                     # the face's inside
    R = T["face_radius_x"]
    y_def = y_face + T["deflection_centre_behind_face"]
    rn = T["neck_radius"]
    y_neck0 = y_def + 0.03
    y_end = y_face + T["neck_end_behind_face"]
    glass = glow("tube_glass")
    pw, ph = sw + 0.034, sh + 0.030          # panel outside, estimated
    with parts.assembly("picture_tube", internal=True):
        # Panel skirt and funnel: rounded-rectangle sections easing into the round neck.
        rings = []
        for k in range(9):
            t = k / 8
            y = y_in + T["panel_skirt"] * min(1, t * 3) + (y_neck0 - y_in - T["panel_skirt"]) * max(0, (t - 1 / 3) * 1.5)
            if t <= 1 / 3:
                a, b, p = pw / 2, ph / 2, 7.0
            else:
                s = (t - 1 / 3) * 1.5
                e = s ** 0.7
                a = pw / 2 * (1 - e) + rn * e
                b = ph / 2 * (1 - e) + rn * e
                p = 7.0 * (1 - s) + 2.0 * s
            rings.append((y, superellipse(a, b, p)))
        loft_y("bulb", rings, sx, sz, glass)
        loft_y("neck", [(y_neck0, superellipse(rn, rn, 2.0)), (y_end, superellipse(rn, rn, 2.0))],
               sx, sz, glass, cap_back=True)
        # The anode button on the funnel's top, about where the funnel starts to narrow.
        cyl_ya = parts.cylinder("anode_button", 0.006, 0.004, location=(sx, y_in + 0.07, sz + ph / 2 * 0.86),
                                direction=(0, 0, 1), material="gun_metal")
        # Base pins at the neck's end.
        for i in range(12):
            a = 2 * math.pi * i / 12
            parts.cylinder(f"pin_{i + 1}", 0.0005, 0.010, location=(sx + 0.009 * math.cos(a), y_end, sz + 0.009 * math.sin(a)),
                           direction=(0, 1, 0), material="gun_metal", segments=8)
    with parts.assembly("aperture_grille", internal=True):
        # Steel sheet with vertical slits (pitch and open share from ohkoshi_1973), bowed like
        # the face, in a frame whose top and bottom are L-section bars on two side members;
        # damper wires across the strips.
        pitch = sum(G["pitch_small_tubes"]) / 2
        mat, rep = stripes_material("grille_slits", pitch * 8, None, slit=G["centre_transmission"])
        yg = y_in + T["grille_gap"]
        gw, gh = sw + 0.006, sh + 0.006
        curved_sheet("grille", sx, sz, gw, gh, yg, R, mat, uv=(rep, rep))
        sag = R - math.sqrt(R * R - (gw / 2) ** 2)
        for s, nm in ((1, "top"), (-1, "bottom")):
            parts.box(f"frame_{nm}", (gw + 0.012, 0.012, 0.004), location=(sx, yg + 0.006 + sag / 2, sz + s * (gh / 2 + 0.002)),
                      material="grille_steel")
            parts.box(f"frame_{nm}_lip", (gw + 0.012, 0.002, 0.010), location=(sx, yg + 0.012 + sag / 2, sz + s * (gh / 2 + 0.006)),
                      material="grille_steel")
        for s, nm in ((1, "right"), (-1, "left")):
            parts.box(f"frame_{nm}", (0.006, 0.006, gh + 0.012), location=(sx + s * (gw / 2 + 0.003), yg + sag, sz),
                      material="grille_steel")
        for k, fz in enumerate((1 / 3, 2 / 3)):
            z = sz - gh / 2 + gh * fz
            pts = []
            for i in range(17):
                u = -gw / 2 + gw * i / 16
                pts.append((sx + u, yg + R - math.sqrt(R * R - u * u) - 0.0003, z))
            parts.tube(f"damper_wire_{k + 1}", pts, 0.00015, segments=4, material="grille_steel")
    with parts.assembly("phosphor", internal=True):
        mat, rep = stripes_material("phosphor_stripes", pitch * 8, ["#d03030", "#30b040", "#3050d0"])
        curved_sheet("phosphor_screen", sx, sz, sw + 0.004, sh + 0.004, y_in + 0.0003, R, mat, uv=(rep, rep))
    electron_gun(spec, sx, sz, y_def, y_neck0, y_end, rn, y_in + T["grille_gap"], T)


def electron_gun(spec, sx, sz, y_def, y_neck0, y_end, rn, y_grille, T):
    """One gun, three cathodes in line, a common grid 1 and 2, the large focus lens and the
    convergence plates at its top (belt_1972, ohkoshi_1973, us3514663); sizes estimated."""
    cs = T["cathode_spacing"]
    y_k = y_end - 0.022                  # cathodes
    y_lens = y_k - 0.040                 # main lens centre (where the beams cross)
    y_plates = y_lens - 0.022            # convergence plates
    r_e = rn - 0.003
    with parts.assembly("electron_gun", internal=True):
        for i, x in enumerate((-cs, 0, cs)):
            ccx = sx + x
            parts.cylinder(f"cathode_{'rgb'[i]}", 0.0012, 0.008, location=(ccx, y_k, sz), direction=(0, 1, 0),
                           material="gun_metal", segments=12)
        parts.cylinder("grid_1", r_e * 0.8, 0.0008, location=(sx, y_k - 0.002, sz), direction=(0, 1, 0), material="gun_metal")
        parts.cylinder("grid_2", r_e * 0.8, 0.0008, location=(sx, y_k - 0.005, sz), direction=(0, 1, 0), material="gun_metal")
        # The focus lens: three large cylinders (unipotential: grid 3, focus electrode, grid 5).
        for k, (y0, ln) in enumerate(((y_k - 0.007, 0.010), (y_lens + 0.007, 0.014), (y_lens - 0.004, 0.012))):
            parts.cylinder(f"lens_electrode_{k + 1}", r_e, ln, location=(sx, y0, sz), direction=(0, -1, 0),
                           material="gun_metal", segments=32)
        # Convergence plates: an inner pair either side of the green beam, an outer pair
        # outside the red and blue ones.
        for s in (-1, 1):
            parts.box(f"plate_inner_{'l' if s < 0 else 'r'}", (0.0005, 0.018, 0.010),
                      location=(sx + s * 0.0022, y_plates - 0.009, sz), material="gun_metal")
            parts.box(f"plate_outer_{'l' if s < 0 else 'r'}", (0.0005, 0.018, 0.012),
                      location=(sx + s * 0.0085, y_plates - 0.009, sz), material="gun_metal")
        parts.cylinder("getter_ring", r_e * 0.6, 0.002, location=(sx, y_plates - 0.022, sz), direction=(0, 1, 0),
                       material="gun_metal")
    with parts.assembly("yoke", internal=True):
        # Deflection yoke round the neck where the funnel starts, flaring forward.
        prof = [(rn + 0.001, 0.0), (rn + 0.008, 0.0), (rn + 0.020, 0.040), (rn + 0.034, 0.055),
                (rn + 0.024, 0.055), (rn + 0.006, 0.020), (rn + 0.001, 0.010)]
        parts.lathe("yoke_windings", prof, location=(sx, y_neck0 + 0.012, sz), direction=(0, -1, 0),
                    closed=True, material="yoke_copper", segments=48)
        prof2 = [(rn + 0.010, 0.006), (rn + 0.016, 0.006), (rn + 0.026, 0.040), (rn + 0.020, 0.040)]
        parts.lathe("yoke_core", prof2, location=(sx, y_neck0 + 0.012, sz), direction=(0, -1, 0),
                    closed=True, material="black", segments=48)
    with parts.assembly("neck_magnets", internal=True):
        # Four magnets for static convergence (belt_1972), as rings on the neck behind the yoke.
        for k in range(4):
            parts.lathe(f"magnet_{k + 1}", [(rn + 0.001, 0), (rn + 0.006, 0), (rn + 0.006, 0.003), (rn + 0.001, 0.003)],
                        location=(sx, y_neck0 + 0.020 + 0.006 * k, sz), direction=(0, 1, 0), closed=True,
                        material="dark_metal", segments=32)
    with parts.assembly("beams", internal=True):
        # Red and blue bend in, cross green at the lens, fan out, and the plates turn them back
        # to cross again at the grille (belt_1972); all three aimed at the screen's centre here.
        # From the yoke's deflection centre on, the three beams hang from one pivot, which the
        # Beam animation swings across the screen (beam_animation).
        land = y_grille - 0.012
        y_b = y_plates - 0.05
        pivot = bpy.data.objects.new("beam_pivot", None)
        parts.collection().objects.link(pivot)
        parts._tag(pivot)
        pivot.matrix_world = Matrix.Translation((sx, y_def, sz))
        paths = {}
        for i, (x, col) in enumerate(((-cs, "beam_red"), (0, "beam_green"), (cs, "beam_blue"))):
            spread = -x * 0.75                # after the crossing, on the other side
            x_def = sx + spread * 0.7 * (y_def - y_grille) / (y_b - y_grille)
            gun = [(sx + x, y_k - 0.001, sz), (sx + x * 0.5, y_k - 0.012, sz), (sx, y_lens, sz),
                   (sx + spread * 0.6, y_plates, sz), (sx + spread, y_plates - 0.018, sz),
                   (sx + spread * 0.7, y_b, sz), (x_def, y_def, sz)]
            fan = [(x_def, y_def, sz), (sx, y_grille, sz), (sx + x * 0.12, land, sz)]
            mat = glow(col, 2.0)
            parts.tube(f"beam_{col[5:]}", gun, 0.0004, segments=6, material=mat)
            f = parts.tube(f"beam_{col[5:]}_swept", fan, 0.0004, segments=6, material=mat)
            f.parent = pivot
            f.matrix_parent_inverse = pivot.matrix_world.inverted()
            paths[col] = (gun, fan, mat)
        ANIM.update(pivot=pivot, paths=paths, sx=sx, sz=sz, y_def=y_def, land=land)


# --- the Beam animation ----------------------------------------------------------------------

def _along(pts, u):
    """The point a share `u` (0..1) of the way along a polyline."""
    P = [Vector(p) for p in pts]
    seg = [(P[i + 1] - P[i]).length for i in range(len(P) - 1)]
    d = u * sum(seg)
    for i, s in enumerate(seg):
        if d <= s or i == len(seg) - 1:
            return P[i].lerp(P[i + 1], min(1.0, d / s if s else 0.0))
        d -= s


def beam_animation(spec, F):
    """Slow motion (estimates.beam_animation): electrons stream from the three cathodes, cross
    in the lens, are bent back by the convergence plates and land together on the phosphor; the
    yoke swings them across the screen line by line, and each spot glows and fades behind them.
    The real beam draws 525 lines a frame; 64 are drawn here, slowed about 1,900 times."""
    A = spec["estimates"]["beam_animation"]["value"]
    fps = A["fps"]
    sc = bpy.context.scene
    sc.render.fps = fps
    pivot, paths = ANIM["pivot"], ANIM["paths"]
    sx, sz, y_def, land = ANIM["sx"], ANIM["sz"], ANIM["y_def"], ANIM["land"]
    L = F.L
    _, _, sw, sh = F.box(L["screen_opening"])
    R = spec["estimates"]["tube"]["value"]["face_radius_x"]
    D = y_def - land
    n_lines, n_seg = A["lines"], A["segments"]
    t0 = A["to_start"]
    per = A["line"] + A["retrace"]
    t_end_raster = t0 + n_lines * per
    t_end = t_end_raster + A["back"]
    n = int(round(t_end * fps))
    sc.frame_start, sc.frame_end = 0, n
    # The raster overscans the screen (runs on behind the bezel), so the picture fills it.
    X0, X1 = -sw / 2 * A["overscan"], sw / 2 * A["overscan"]
    pitch = sh * A["overscan"] / n_lines
    zs = [sh / 2 * A["overscan"] - pitch * (k + 0.5) for k in range(n_lines)]
    sag = lambda x: R - math.sqrt(R * R - x * x)

    def aim(x, z):
        """Pivot rotation (x, z euler) and y scale that put the beams' end on the phosphor at (x, z)."""
        d = Vector((x, -(D - sag(x)), z))
        ln = d.length
        d.normalize()
        return math.asin(-d.z), math.atan2(d.x, -d.y), ln / D

    def target(t):
        """Where the beams land at time t (screen x, z from its centre)."""
        if t <= t0:
            s = smoothstep(t / t0)
            return X0 * s, zs[0] * s
        if t >= t_end_raster:
            s = smoothstep(min(1.0, (t - t_end_raster) / A["back"]))
            return X1 * (1 - s), zs[-1] * (1 - s)
        k = min(n_lines - 1, int((t - t0) / per))
        u = (t - t0 - k * per)
        x0, x1 = X0, X1
        if u <= A["line"]:
            return x0 + (x1 - x0) * u / A["line"], zs[k]
        # retrace: back to the left, down to the next line
        r = smoothstep((u - A["line"]) / A["retrace"])
        zn = zs[min(k + 1, n_lines - 1)]
        return x1 + (x0 - x1) * r, zs[k] + (zn - zs[k]) * r

    # Electron packets: on the gun's path (fixed) and on the swept path (riding the pivot).
    packets = []
    with parts.assembly("beams", internal=True):
        for col, (gun, fan, mat) in paths.items():
            for j in range(A["packets"]):
                g = parts.cylinder(f"electrons_{col[5:]}_{j + 1}", 0.0009, 0.0018, location=gun[0],
                                   direction=(0, -1, 0), material=glow(col, 6.0), segments=8)
                f = parts.cylinder(f"electrons_{col[5:]}_{j + 1}_swept", 0.0009, 0.0018, location=fan[0],
                                   direction=(0, -1, 0), material=glow(col, 6.0), segments=8)
                f.parent = pivot
                f.matrix_parent_inverse = pivot.matrix_world.inverted()
                packets.append((g, f, gun, fan, j))
        # The landing spot.
        spot = parts.cylinder("beam_spot", A["spot"], 0.0006, location=(sx, land + 0.0004, sz), direction=(0, -1, 0),
                              material=glow("phosphor_glow", 8.0), segments=16)
        spot.parent = pivot
        spot.matrix_parent_inverse = pivot.matrix_world.inverted()
    # The phosphor where the spot passed: each line in short pieces that light as the spot
    # reaches them ("show_from") and fade behind it ("fade_out"); on the face's outside, where the
    # picture is seen (the glass is drawn opaque).
    with parts.assembly("phosphor_glow", internal=True):
        h = pitch * A["line_fill"]
        face = lambda x: land - 0.010 + sag(x) - 0.0003
        seg = (X1 - X0) / n_seg
        for k, z in enumerate(zs):
            for j in range(n_seg):
                xa, xb = X0 + j * seg - 0.0003, X0 + (j + 1) * seg + 0.0003
                verts = [(sx + xa, face(xa), sz + z - h / 2), (sx + xb, face(xb), sz + z - h / 2),
                         (sx + xb, face(xb), sz + z + h / 2), (sx + xa, face(xa), sz + z + h / 2)]
                o = _solid(f"glow_{k + 1}_{j + 1}", verts, [(0, 1, 2, 3)], glow("phosphor_glow", 3.0))
                t_hit = t0 + k * per + A["line"] * (j + 0.5) / n_seg
                o["show_from"] = round(t_hit, 4)
                o["fade_out"] = [round(t_hit + 0.05, 4), round(t_hit + 0.05 + A["persist"], 4)]
                o.hide_render = True    # dark at rest: left out of the sheet (still exported)

    total = {}
    for g, f, gun, fan, j in packets:
        lg = sum((Vector(gun[i + 1]) - Vector(gun[i])).length for i in range(len(gun) - 1))
        lf = sum((Vector(fan[i + 1]) - Vector(fan[i])).length for i in range(len(fan) - 1))
        total[g.name] = (lg, lf)
    rest = {o.name: o.location.copy() for o in [p[0] for p in packets] + [p[1] for p in packets]}
    for fr in range(n + 1):
        t = fr / fps
        on = 0.0 < t < t_end
        x, z = target(t)
        rx, rz, sy = aim(x, z)
        pivot.rotation_mode = "XYZ"
        pivot.rotation_euler = (rx, 0, rz)
        pivot.scale = (1, sy, 1)
        pivot.keyframe_insert("rotation_euler", frame=fr)
        pivot.keyframe_insert("scale", frame=fr)
        for g, f, gun, fan, j in packets:
            lg, lf = total[g.name]
            u = ((t / A["packet_period"]) + j / A["packets"]) % 1.0
            d = u * (lg + lf)
            if d <= lg:
                g.location = rest[g.name] + (_along(gun, d / lg) - Vector(gun[0]))
                g.scale = (1, 1, 1) if on else (0, 0, 0)
                f.scale = (0, 0, 0)
            else:
                f.location = rest[f.name] + (_along(fan, (d - lg) / lf) - Vector(fan[0]))
                f.scale = (1, 1, 1) if on else (0, 0, 0)
                g.scale = (0, 0, 0)
            for o in (g, f):
                o.keyframe_insert("location", frame=fr)
                o.keyframe_insert("scale", frame=fr)
        spot.scale = (1, 1, 1) if on else (0, 0, 0)
        spot.keyframe_insert("scale", frame=fr)
    for o in [pivot, spot] + [p[0] for p in packets] + [p[1] for p in packets]:
        if o.animation_data and o.animation_data.action:
            for fc in _fcurves(o.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    sc.frame_set(0)


def _fcurves(action):
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                out += list(bag.fcurves)
    return out


def smoothstep(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


# --- the chassis (stand-in from the KV-7010UA's board list, layout estimated) ---------------

def board(name, x, y, z, w, d, along, seed, parts_count=40):
    """A printed circuit board `w` x `d` (thickness 1.6 mm) and its parts, seeded so every
    build places them the same. `along`: "xy" lies flat (parts on top), "yz" stands upright
    facing -x (parts on that side), "zy" the same facing +x, "xz" stands upright facing -y."""
    rng = np.random.default_rng(seed)
    t = 0.0016
    if along == "xy":
        size, nrm = (w, d, t), (0, 0, 1)
    elif along in ("yz", "zy"):
        size, nrm = (t, w, d), (-1 if along == "yz" else 1, 0, 0)
    else:
        size, nrm = (w, t, d), (0, -1, 0)
    parts.box(name, size, location=(x, y, z), material="pcb")
    n = Vector(nrm)
    # in-plane axes
    a1, a2 = {"xy": ((1, 0, 0), (0, 1, 0)), "yz": ((0, 1, 0), (0, 0, 1)), "zy": ((0, 1, 0), (0, 0, 1)), "xz": ((1, 0, 0), (0, 0, 1))}[along]
    a1, a2 = Vector(a1), Vector(a2)
    base = Vector((x, y, z)) + n * (t / 2)
    for i in range(parts_count):
        p = base + a1 * rng.uniform(-w / 2 + 0.008, w / 2 - 0.008) + a2 * rng.uniform(-d / 2 + 0.008, d / 2 - 0.008)
        kind = rng.choice(["cap", "can", "res", "res", "res"])
        if kind == "cap":
            r, h = rng.uniform(0.003, 0.006), rng.uniform(0.010, 0.020)
            parts.cylinder(f"{name}_c{i}", r, h, location=tuple(p), direction=tuple(n), material="capacitor", segments=12)
        elif kind == "can":
            parts.cylinder(f"{name}_q{i}", 0.0045, 0.006, location=tuple(p), direction=tuple(n), material="gun_metal", segments=12)
        else:
            dims = a1 * 0.009 + a2 * 0.0025 + n * 0.005
            parts.box(f"{name}_r{i}", tuple(abs(v) for v in dims), location=tuple(p + n * 0.0025), material="resistor")


def chassis(spec, F):
    E = spec["estimates"]["chassis"]["value"]
    L = F.L
    W, t, z0, H = F.W, F.wall, F.feet, F.H
    yf = F.y_front + F.recess + 0.004       # behind the front panel
    yb = F.sleeve_back - 0.035              # in front of the back panel
    sx, sz, sw, sh = F.box(L["screen_opening"])
    x_col = F.x((L["column"][0] + L["column"][2]) / 2)
    with parts.assembly("chassis", internal=True):
        # A steel tray on the cabinet floor carries everything.
        parts.box("chassis_tray", (W - 2 * t - 0.004, yb - yf - 0.01, 0.0015),
                  location=(0, (yf + yb) / 2, z0 + t + 0.00075), material="dark_metal")
    C = spec["estimates"]["chassis_kv7010"]["value"]
    with parts.assembly("board_sd", internal=True):
        # Upright on the left, beside the tube's cone, parts facing the tube (Sams side view).
        bw, bh = C["sd_board"]
        board("board_sd", -W / 2 + t + 0.012, yb - bw / 2 - 0.005, z0 + t + 0.01 + bh / 2, bw, bh, "zy", 1, 60)
    with parts.assembly("power_transformer", internal=True):
        # PT under the HV section at the back (Sams top and bottom views).
        px_, py_, pz_ = C["pt"]
        x, y, z = sx + 0.10, yb - 0.045, z0 + t + 0.0015
        parts.box("pt_core", (px_, py_, pz_), location=(x, y, z + pz_ / 2), material="dark_metal")
        parts.box("pt_winding", (px_ * 0.5, py_ + 0.008, pz_ * 0.7), location=(x, y, z + pz_ * 0.45), material="yoke_copper")
        parts.box("pt_clamp", (px_ + 0.006, py_ * 0.3, 0.003), location=(x, y, z + pz_ + 0.0015), material="gun_metal")
    with parts.assembly("board_cv", internal=True):
        board("board_cv", x_col - 0.045, yf + 0.13, z0 + t + 0.11, 0.16, 0.17, "yz", 2, 45)
    with parts.assembly("board_power", internal=True):
        board("board_power", x_col, yb - 0.04, z0 + t + 0.07, 0.10, 0.11, "xz", 3, 25)
    with parts.assembly("board_rv", internal=True):
        board("board_rv", x_col, yb - 0.04, z0 + t + 0.20, 0.10, 0.09, "xz", 4, 18)
    with parts.assembly("board_n", internal=True):
        # The tube socket board on the neck's end.
        T = spec["estimates"]["tube"]["value"]
        y_end = F.y_front + F.recess + 0.004 + T["neck_end_behind_face"]
        board("board_n", sx, y_end + 0.014, sz, 0.05, 0.05, "xz", 5, 6)
    with parts.assembly("hv_rectifier", internal=True):
        # V801, a 1S2/DY86 vacuum diode beside the flyback: glass bulb, its anode inside, a cap on top.
        rd, rl = C["rectifier"]
        rx, ry, rz = sx + 0.085, yb - 0.06, z0 + H * 0.66
        parts.cylinder("v801_socket", rd * 0.75, 0.008, location=(rx, ry, rz), direction=(0, 0, 1), material="black", segments=16)
        parts.lathe("v801_bulb", [(0, 0), (rd / 2, 0), (rd / 2, rl * 0.85), (rd * 0.3, rl), (0, rl)],
                    location=(rx, ry, rz + 0.008), material="tube_glass", segments=20)
        parts.cylinder("v801_anode", rd * 0.25, rl * 0.45, location=(rx, ry, rz + 0.008 + rl * 0.25), direction=(0, 0, 1),
                       material="gun_metal", segments=12)
        parts.cylinder("v801_cap", rd * 0.18, 0.004, location=(rx, ry, rz + 0.008 + rl), direction=(0, 0, 1),
                       material="gun_metal", segments=12)
    with parts.assembly("horizontal_output", internal=True):
        # HOT and the damper diode below the flyback; Q801 on a finned heat sink (Sams top view).
        hx_, hy_, hz_ = C["hot"]
        x, y, z = sx + 0.10, yb - 0.025, z0 + H * 0.45
        parts.box("hot_core", (hx_, hy_, hz_), location=(x, y, z), material="black")
        parts.cylinder("hot_winding", hx_ * 0.38, hy_ + 0.006, location=(x, y - hy_ / 2 - 0.003, z), direction=(0, 1, 0),
                       material="yoke_copper", segments=16)
        parts.cylinder("damper_diode", 0.003, 0.012, location=(x + hx_ / 2 + 0.006, y - 0.006, z - hz_ / 2),
                       direction=(0, 1, 0), material="black", segments=10)
        kx, ky, kz = x + 0.05, yb - 0.02, z0 + H * 0.40
        parts.box("q801_sink", (0.002, 0.03, 0.035), location=(kx, ky, kz), material="foil_silver")
        for i in range(4):
            parts.box(f"q801_fin_{i}", (0.012, 0.0015, 0.035), location=(kx + 0.007, ky - 0.012 + i * 0.008, kz), material="foil_silver")
        parts.box("q801", (0.004, 0.012, 0.016), location=(kx - 0.003, ky, kz), material="black")
    with parts.assembly("flyback", internal=True):
        # High-voltage transformer behind the tube, its lead to the anode button.
        fx, fy, fz = sx + 0.12, yb - 0.06, z0 + H * 0.72
        parts.box("flyback_core", (0.04, 0.03, 0.05), location=(fx, fy, fz), material="black")
        parts.cylinder("flyback_winding", 0.017, 0.035, location=(fx, fy - 0.03, fz), direction=(0, 1, 0),
                       material="yoke_copper", segments=24)
        ph = sh + 0.030
        parts.tube("hv_lead", [(fx, fy - 0.02, fz + 0.025), (fx - 0.05, fy - 0.08, sz + ph / 2 * 0.95),
                               (sx, yf + 0.08, sz + ph / 2 * 0.86 + 0.004)], 0.0025, segments=8,
                   bend_radius=0.03, material="black")
    with parts.assembly("tuner", internal=True):
        # Drum VHF tuner behind the channel dial, on the dial's shaft.
        du, dv = L["dial_centre"]
        tw, th, td = E["tuner"]
        x, z = F.x(du), F.z(dv)
        parts.box("tuner_can", (tw, td, th), location=(x, yf + 0.008 + td / 2, z), material="foil_silver")
        parts.cylinder("tuner_shaft", 0.003, 0.012, location=(x, yf - 0.004, z), direction=(0, 1, 0), material="gun_metal")
    with parts.assembly("controls", internal=True):
        # A potentiometer behind each knob.
        for i, u in enumerate(L["knobs_u"] + [L["power_knob"][0]]):
            v = L["knob_v"] if i < 4 else L["power_knob"][1]
            parts.cylinder(f"pot_{i + 1}", 0.008, 0.010, location=(F.x(u), yf, F.z(v)), direction=(0, 1, 0),
                           material="dark_metal", segments=16)
    with parts.assembly("speaker_unit", internal=True):
        sw_, sh_, sd = E["speaker"]
        qx, qz, _, _ = F.box(L["speaker"])
        prof = [(0.0, 0.0), (0.008, 0.0), (0.008, 0.010), (sw_ / 2 * 0.95, sd), (sw_ / 2, sd), (sw_ / 2, sd + 0.002),
                (0.0, sd + 0.002)]
        cone = parts.lathe("speaker_cone", prof, location=(qx, yf + sd + 0.006, qz), direction=(0, -1, 0),
                           material="speaker_cone", segments=32)
        cone.scale = (1, 1, sh_ / sw_)  # elliptical (radiomuseum_kv1310e)
        cone.data.transform(Matrix.Diagonal((1, 1, 1, 1)))
        parts.cylinder("speaker_magnet", 0.015, 0.012, location=(qx, yf + sd + 0.006, qz), direction=(0, 1, 0),
                       material="dark_metal", segments=24)


# --- surface detail -----------------------------------------------------------------------

def quad(name, x0, z0, w, h, y, material):
    """A flat picture facing -y, its image's bottom-left at (x0, z0), w by h."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((x0, y, z0), (x0 + w, y, z0), (x0 + w, y, z0 + h), (x0, y, z0 + h))]
    f = bm.faces.new(vs)
    if f.normal.y > 0:
        f.normal_flip()
    uv = bm.loops.layers.uv.new("UVMap")
    for loop in f.loops:
        p = loop.vert.co
        loop[uv].uv = ((p.x - x0) / w, (p.z - z0) / h)
    return parts._object(name, bm, material, Matrix(), None)


def label(name, layers, F, box, y, metallic=0.5):
    """A printed label over a [u0, v0, u1, v1] box: masks from refs/kv1310/labels, each in a
    spec colour (drawn by refs/kv1310/markings-draw.py)."""
    M = SPEC[0]["materials"]
    img = textures.marking(name, [(os.path.join(LABELS, f), materials.colour(M[c])) for f, c in layers], TEX)
    mat = materials.image(name, img, metallic=metallic, roughness=0.35, cutout=True)
    cx, cz, w, h = F.box(box)
    return quad(name, cx - w / 2, cz - h / 2, w, h, y, mat)


def labels(F):
    L = F.L
    yf, ip = F.y_front, F.recess
    with parts.assembly("bezel"):
        label("sony_letters", [("sony_plate.png", "letter_silver")], F, L["sony_plate"], yf + ip - 0.0056)
    with parts.assembly("front_panel"):
        label("front_text", [("front_text.png", "letter_silver")], F, L["front_text_box"], yf + ip - 0.0003)
    with parts.assembly("control_column"):
        label("badge_print", [("badge_text.png", "letter_silver"), ("badge_blue.png", "badge_blue"),
                              ("badge_red.png", "badge_red"), ("badge_green.png", "badge_green")],
              F, L["badge"], yf + ip - 0.0062, metallic=0.0)
        label("color_print", [("color_plate.png", "letter_silver")], F, L["color_plate"], yf + ip - 0.0073)
    with parts.assembly("channel_dial"):
        du, dv = L["dial_centre"]
        R = L["dial_r"] * 0.86
        label("dial_numbers", [("dial_numbers.png", "letter_silver")], F,
              [du - R, dv - R, du + R, dv + R], yf + ip - 0.0122)


def dial_joint(F):
    """The channel dial turns on its shaft (the spec's joints.dial_turn: a click in the viewer
    turns it); the whole dial is on the joint, ring included, so a click anywhere on it turns it
    rather than focusing it, as the Land Camera's knob."""
    L = F.L
    du, dv = L["dial_centre"]
    with parts.assembly("channel_dial"):
        j = parts.joint("dial_turn", (F.x(du), F.y_front, F.z(dv)), axis=(0, 1, 0))
    bpy.context.view_layer.update()          # the grip's turn must be in matrix_world first
    for o in [ob for ob in parts.collection().objects if ob.name.startswith(("dial_ring", "dial_face", "dial_hub", "dial_grip", "dial_numbers"))]:
        mw = o.matrix_world.copy()
        o.parent = j
        o.matrix_world = mw


def walnut(spec):
    """Walnut veneer on the sleeve: long streaks along the wrap (across the top, down the sides),
    the sampled colour lightened and darkened by up to a quarter (grain estimated)."""
    m = spec["materials"]["walnut"]
    w, h, rep_u, rep_v = 1024, 256, 0.6, 0.15
    mpp_u, mpp_v = rep_u / w, rep_v / h
    n = tiling._noise(h, w, 0.0012 / mpp_v, 0.25 / mpp_u, 11)              # fine streaks
    n += 0.6 * tiling._noise(h, w, 0.006 / mpp_v, 0.4 / mpp_u, 12)         # broader bands
    U = np.arange(w)[None, :] / w
    V = np.arange(h)[:, None] / h
    fig = np.sin(2 * np.pi * (V * 6 + 0.35 * np.sin(2 * np.pi * U * 2)))   # gentle figure
    shade = 1 + 0.10 * n + 0.04 * fig
    col = tiling.srgb(m["hex"])[None, None] * shade[..., None]
    base = tiling.image("kv1310", "walnut_base", np.clip(col, 0, 1).astype(np.float32), "sRGB")
    mat = materials.image("walnut_veneer", base, metallic=0.0, roughness=m["roughness"])
    for nm in ("sleeve_top", "sleeve_bottom", "sleeve_left", "sleeve_right"):
        obj = parts.collection().objects[nm]
        me, mw = obj.data, obj.matrix_world
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            nz = abs(poly.normal.z)
            for li in poly.loop_indices:
                q = mw @ me.vertices[me.loops[li].vertex_index].co
                along = q.x if nz > 0.5 else q.z     # the grain runs round the wrap
                uv.data[li].uv = (along / rep_u, q.y / rep_v)
        obj.material_slots[0].material = mat


def speaker_holes(spec, F):
    """The speaker panel's square grid of holes (pitch from the photo, hole size by eye)."""
    S = spec["from_photos"]["speaker_holes"]["value"]
    m = spec["materials"]["speaker_grille"]
    px, k = 256, 8                          # 8 x 8 holes per tile, 32 px each: every mipmap level
                                            # halves whole holes, so the zoomed-out grille is even grey
    rep = S["pitch"] * k
    mpp = rep / px
    yy, xx = np.mgrid[0:px, 0:px] * mpp
    d = np.hypot((xx % S["pitch"]) - S["pitch"] / 2, (yy % S["pitch"]) - S["pitch"] / 2)
    hole = np.clip((S["hole"] / 2 - d) / mpp + 0.5, 0, 1)
    col = tiling.srgb(m["hex"])[None, None] * (1 - 0.85 * hole)[..., None]
    base = tiling.image("kv1310", "speaker_base", np.clip(col, 0, 1).astype(np.float32), "sRGB")
    mat = materials.image("speaker_perforated", base, metallic=m["metallic"], roughness=m["roughness"])
    obj = parts.collection().objects["speaker"]
    while obj.data.uv_layers:
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
    tiling.plane_uv(obj, (1, 0), rep, rep)
    obj.material_slots[0].material = mat


def build(spec):
    SPEC[0] = spec
    F = Front(spec)
    cabinet(F)
    front_panel(F)
    screen(F)
    handle(F, spec)
    back_cover(F)
    picture_tube(spec, F)
    chassis(spec, F)
    labels(F)
    dial_joint(F)
    walnut(spec)
    speaker_holes(spec, F)
    beam_animation(spec, F)
