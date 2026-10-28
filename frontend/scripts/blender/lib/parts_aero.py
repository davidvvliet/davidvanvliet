# Shared parts: lofted bodies and lifting surfaces (fuselage sections, wings, tails and fins,
# their control surfaces, grid fins). Imported through lib/parts.py.
import contextlib, math
import bmesh, bpy
from mathutils import Matrix, Vector

from . import materials
from .parts_core import _object

# --- Aircraft shapes ------------------------------------------------------------------

def section(half_width, top, bottom, n=32, exponent=2.0, y=0.0):
    """A closed cross-section as (y, z) points: a superellipse `half_width` wide each side,
    from `bottom` to `top` (z), centred on `y`. `exponent` 2 is an ellipse; larger is boxier.
    Points go round counter-clockwise seen from +x, starting at the top."""
    zc, h = (top + bottom) / 2, (top - bottom) / 2
    pts = []
    for k in range(n):
        a = math.pi / 2 + 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        pts.append((y + half_width * math.copysign(abs(c) ** (2 / exponent), c),
                    zc + h * math.copysign(abs(s) ** (2 / exponent), s)))
    return pts

def _loft(bm, rings):
    vs = [[bm.verts.new(Vector(p)) for p in ring] for ring in rings]
    n = max(len(r) for r in vs)
    for a, b in zip(vs, vs[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[k2], b[k]))
            elif len(b) == 1:
                bm.faces.new((a[k], a[k2], b[0]))
            else:
                bm.faces.new((a[k], a[k2], b[k2], b[k]))
    caps = [bm.faces.new(end) for end in (vs[0], vs[-1]) if len(end) > 2]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.index_update()
    return [f.index for f in caps]

def loft(name, rings, material="white_paint", smooth=True, parent=None):
    """Skin through closed rings of (x, y, z) points (a fuselage, a fairing, a canopy): every
    ring has the same number of points, or one point for a pointed end. Open ends are capped."""
    bm = bmesh.new()
    caps = _loft(bm, rings)
    obj = _object(name, bm, material, Matrix(), parent, smooth=smooth)
    for i in caps:  # flat caps, so smooth shading doesn't round the edge
        obj.data.polygons[i].use_smooth = False
    return obj

def fuselage(name, stations, n=32, material="white_paint", parent=None):
    """A body along +x from `stations` [(x, half_width, top, bottom[, exponent]), ...] in
    order. A station with half_width 0 is a point (nose tip or tail cone end), at z midway."""
    rings = []
    for st in stations:
        x, w, top, bottom = st[:4]
        if w <= 0:
            rings.append([(x, 0.0, (top + bottom) / 2)])
        else:
            rings.append([(x, y, z) for y, z in section(w, top, bottom, n, st[4] if len(st) > 4 else 2.0)])
    return loft(name, rings, material, parent=parent)

def _half_thickness(kind, thickness, x):
    """Half-thickness (fraction of chord) at chord fraction x: "lens" is a symmetric
    biconvex section (sharp edges), "wedge" a single wedge with a blunt base."""
    if kind == "lens":
        return 2 * thickness * x * (1 - x)
    if kind == "wedge":
        return thickness / 2 * x
    raise ValueError(kind)

def surface(name, root_le, root_chord, tip_le, tip_chord, thickness, kind="lens",
            chord_dir=(-1, 0, 0), chords=9, material="white_paint", parent=None,
            span=(0.0, 1.0), chord=(0.0, 1.0), side=0, offset=0.0):
    """A wing, tail or fin: a trapezoid from the root chord (leading edge at `root_le`) to the
    tip chord (leading edge at `tip_le`), each chord running along `chord_dir` (aft). The
    section is `kind` ("lens" or "wedge"), `thickness` a fraction of the chord (a wedge's is
    its base). Thickness is across the plane of the span and chord.
    A piece of it (a control surface, speed brake or painted band): `span` and `chord` are the
    fractions it covers, `side` +1 or -1 builds only the half on that side of the mid-plane
    (+1 is along (tip - root) x chord_dir), and `offset` (m) stands it out from the surface.
    `chord` can also be a pair of pairs, the fractions at the piece's inner and outer end (a
    flap whose hinge line is swept differently from the edges)."""
    cd = Vector(chord_dir).normalized()
    r0, t0 = Vector(root_le), Vector(tip_le)
    normal = (t0 - r0).cross(cd).normalized()
    ends = chord if isinstance(chord[0], (tuple, list)) else (chord, chord)
    def ring(s):
        c0, c1 = ends[0] if s == span[0] else ends[1]
        xs = [c0 + (c1 - c0) * (0.5 - 0.5 * math.cos(math.pi * i / (chords - 1))) if kind == "lens"
              else c0 + (c1 - c0) * i / (chords - 1) for i in range(chords)]
        le, c = r0 + (t0 - r0) * s, root_chord + (tip_chord - root_chord) * s
        pt = lambda x, h: tuple(le + cd * (x * c) + normal * h)
        hs = [_half_thickness(kind, thickness, x) * c + offset for x in xs]
        up = [pt(x, h) for x, h in zip(xs, hs)]
        if side:
            up = [pt(x, side * h) for x, h in zip(xs, hs)]
            return up + [pt(xs[-1], 0.0), pt(xs[0], 0.0)]
        lo = [pt(x, -h) for x, h in zip(reversed(xs), reversed(hs))]
        if hs[-1] <= 1e-12:  # sharp trailing edge: both surfaces share it
            lo = lo[1:]
        if hs[0] <= 1e-12:   # sharp leading edge
            lo = lo[:-1]
        return up + lo
    bm = bmesh.new()
    _loft(bm, [ring(span[0]), ring(span[1])])
    return _object(name, bm, material, Matrix(), parent, smooth=False)

def _notched_wall(bm, a, b, h, notch, wall, notch_top=None):
    """A thin wall standing on the plan segment a-b (local z up), 2h tall and centred on
    z = 0. `notch` cuts a V into its bottom edge at the middle, `notch_top` into its top
    (default: the same as the bottom)."""
    nt = notch if notch_top is None else notch_top
    a, b, up = Vector(a), Vector(b), Vector((0, 0, 1))
    side = (b - a).cross(up).normalized() * (wall / 2)
    m = (a + b) / 2
    outline = [a - up * h, m - up * (h - notch), b - up * h, b + up * h, m + up * (h - nt),
               a + up * h]
    front = [bm.verts.new(p + side) for p in outline]
    back = [bm.verts.new(p - side) for p in outline]
    bm.faces.new(list(reversed(front)))
    bm.faces.new(back)
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new((front[i], front[j], back[j], back[i]))

def grid_fin(name, span, width, thickness, pitch, location=(0, 0, 0), direction=(1, 0, 0),
             up=(0, 0, 1), wall=0.05, notch=0.0, notch_top=None, material="dark_metal",
             parent=None):
    """A lattice grid fin: a rectangular frame `span` out from `location` (the middle of its
    root edge) along `direction`, `width` across and `thickness` deep along `up`, filled with
    two families of walls at +-45 degrees, `pitch` apart. `notch` cuts a V into the top and
    bottom edge of every wall between crossings (the serrated edges of Starship's fins);
    `notch_top` sets the top edge's separately (default: the same)."""
    n = Vector(direction).normalized()
    v = Vector(up) - n * Vector(up).dot(n)
    v.normalize()
    m = Matrix((n, v.cross(n), v)).transposed().to_4x4()   # local x out, y across, z up
    m.translation = Vector(location)
    bm = bmesh.new()
    h, w2 = thickness / 2, width / 2
    step = pitch * math.sqrt(2)          # spacing of one family's lines along x
    eps = 1e-6
    lines = [-w2 - span + step / 2 + j * step for j in range(int((span + 2 * w2) / step) + 2)]
    edge_hits = {"side": set(), "tip": set()}
    for k in (1, -1):
        d = Vector((1, k, 0)) / math.sqrt(2)
        for c in lines:                  # the line x - k*y = c, through (c, 0)
            p0 = Vector((c, 0, 0))
            ts = []
            for t in ((-c) * math.sqrt(2), (span - c) * math.sqrt(2),
                      (-w2) * k * math.sqrt(2), w2 * k * math.sqrt(2)):
                p = p0 + d * t
                if -eps <= p.x <= span + eps and -w2 - eps <= p.y <= w2 + eps:
                    ts.append(t)
            if len(ts) < 2 or max(ts) - min(ts) < eps:
                continue
            t0, t1 = min(ts), max(ts)
            for t in (t0, t1):
                p = p0 + d * t
                if abs(abs(p.y) - w2) < 1e-5:
                    edge_hits["side"].add(round(p.x, 5))
                elif abs(p.x - span) < 1e-5:
                    edge_hits["tip"].add(round(p.y, 5))
            # The other family's lines (x + k*y = c') cross this one at t = (c' - c) / sqrt2.
            cuts = sorted({t0, t1} | {(c2 - c) / math.sqrt(2) for c2 in lines
                                      if t0 < (c2 - c) / math.sqrt(2) < t1})
            for s, e in zip(cuts, cuts[1:]):
                full = e - s > pitch * 0.9
                _notched_wall(bm, p0 + d * s, p0 + d * e, h, notch if full else 0.0, wall,
                              (notch if notch_top is None else notch_top) if full else 0.0)
    # The frame: notched between the points where the lattice meets it; the root edge (on
    # the vehicle) stays straight.
    def frame_edge(a, b, along):
        a, b = Vector(a), Vector(b)
        L = (b - a).length
        cuts = sorted({0.0, L} | {x for x in along if eps < x < L - eps})
        for s, e in zip(cuts, cuts[1:]):
            _notched_wall(bm, a + (b - a) * (s / L), a + (b - a) * (e / L), h,
                          notch if e - s > pitch * 0.5 else 0.0, wall,
                          (notch if notch_top is None else notch_top) if e - s > pitch * 0.5 else 0.0)
    frame_edge((0, -w2, 0), (span, -w2, 0), edge_hits["side"])
    frame_edge((0, w2, 0), (span, w2, 0), edge_hits["side"])
    frame_edge((span, -w2, 0), (span, w2, 0), [y + w2 for y in edge_hits["tip"]])
    frame_edge((0, -w2, 0), (0, w2, 0), [])
    return _object(name, bm, material, m, parent)

