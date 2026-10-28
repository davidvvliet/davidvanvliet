# Rocket and jet engines, built from an engine spec's "engine" block (every number sourced, as
# in any spec). An engine is a model of its own (specs/<engine>.json + a two-line probe) and a
# part other models use: a vehicle lists it in its spec's "engines" and calls `place`, so the
# vehicle is marked behind when the engine's spec changes and carries the engine's credits.
#
# Frame: the thrust axis is local z, pointing up through the engine; the nozzle exit (a jet's
# exhaust plane) is at z = 0 and the engine stands above it. `place` moves it into a vehicle.
#
# Rocket ("kind": "rocket"), lengths in metres:
#   nozzle:    exit_diameter, throat_diameter or area_ratio, length (throat to exit, along the
#              axis), wall, contour: "parabola" (initial_angle_deg, exit_angle_deg: a quadratic
#              Bezier from the throat to the exit with those wall angles, the usual approximation
#              of a thrust-optimised bell), "cone" (straight wall) or "traced" (profile: [[r, z],
#              ...] as fractions of the exit radius and of the length, measured from a side photo,
#              from the exit up to the throat)
#   chamber:   diameter, length (cylinder), convergent_length (throat to the cylinder)
#   powerhead: diameter, height (injector dome and the block above it)
#   gimbal:    diameter, height (the mount on top), optional
#   parts:     [{"kind": "pump" | "pipe" | "box" | "actuator", "name": ..., ...}, ...] in the
#              engine's frame: pump {diameter, length, at, axis}, pipe {diameter, points},
#              box {size, at}, actuator {diameter, from, to}; each with its own source
#   materials: {"nozzle", "chamber", "powerhead", "parts"}: material names (spec or shared)
# Jet ("kind": "jet"), the intake at the top (z = length), exhaust at z = 0:
#   nacelle:   length, max_diameter, inlet_diameter, exit_diameter, wall; optional profile
#              [[r, z], ...] (fractions of max radius and length) traced from a side photo
#   fan:       diameter, hub_diameter, blades, depth (inlet to fan face), pitch_deg, chord
#   spinner:   length
#   core:      exit_diameter, plug_length (the exhaust cone behind the core), optional
#   materials: {"nacelle", "fan", "spinner", "core"}
#
# Every leaf may be a bare value or {"value": ..., "source": ...}. `lod="simple"` drops the
# parts, the fan's blades and most segments, for vehicles with many engines.
import json, math, os
import bmesh
from mathutils import Matrix, Vector
from lib import parts

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _v(x):
    """A spec leaf's value: {"value": v, ...} or v itself (lists and dicts recursively)."""
    if isinstance(x, dict):
        return _v(x["value"]) if "value" in x else {k: _v(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_v(i) for i in x]
    return x

def load(spec, engine):
    """The "engine" block of specs/<engine>.json, for a vehicle whose spec lists it in
    "engines" (that list is what marks the vehicle behind when the engine changes)."""
    if engine not in spec.get("engines", []):
        raise ValueError(f"{engine}: list it in the spec's \"engines\" before using it")
    with open(os.path.join(HERE, "specs", f"{engine}.json")) as f:
        return json.load(f)["engine"]

# --- Rocket ----------------------------------------------------------------------------

def nozzle_profile(nz, steps=24):
    """The nozzle's inner wall as [(r, z)] from the exit (z = 0) up to the throat
    (z = length)."""
    re = nz["exit_diameter"] / 2
    rt = nz["throat_diameter"] / 2 if "throat_diameter" in nz else re / math.sqrt(nz["area_ratio"])
    L = nz["length"]
    kind = nz.get("contour", "parabola")
    if kind == "traced":
        pts = [(r * re, z * L) for r, z in nz["profile"]]
        return [(re, 0.0)] + [p for p in pts if 0 < p[1] < L] + [(rt, L)]
    if kind == "cone":
        return [(re + (rt - re) * i / steps, L * i / steps) for i in range(steps + 1)]
    # Quadratic Bezier, x downstream from the throat: from (0, rt) leaving at the initial wall
    # angle, to (L, re) arriving at the exit angle; the control point is where the two
    # tangents meet.
    tn, te = math.radians(nz["initial_angle_deg"]), math.radians(nz["exit_angle_deg"])
    xq = (re - rt - L * math.tan(te)) / (math.tan(tn) - math.tan(te))
    q = (xq, rt + xq * math.tan(tn))
    out = []
    for i in range(steps + 1):
        t = 1 - i / steps                               # exit first
        x = 2 * t * (1 - t) * q[0] + t * t * L
        r = (1 - t) ** 2 * rt + 2 * t * (1 - t) * q[1] + t * t * re
        out.append((r, L - x))
    return out

def _rocket(name, e, lod):
    nz, ch, ph = e["nozzle"], e["chamber"], e["powerhead"]
    mats = e.get("materials", {})
    seg = 64 if lod == "full" else 20
    wall = nz.get("wall", 0.01)
    inner = nozzle_profile(nz, 24 if lod == "full" else 10)
    L = nz["length"]
    rt = inner[-1][0]
    # Nozzle: a hollow shell, open at both ends (the chamber closes the top).
    outer = [(r + wall, z) for r, z in inner]
    ring = outer + [(r, z) for r, z in reversed(inner)]
    objs = [parts.lathe(f"{name}_nozzle", ring, closed=True, segments=seg,
                        material=mats.get("nozzle", "dark_metal"))]
    # Chamber: from the throat, a cosine blend out to the chamber's radius over the convergent
    # length, the cylinder, then the injector dome into the powerhead.
    rc = ch["diameter"] / 2
    zc = L + ch["convergent_length"]
    prof = [(rt + wall, L - wall)]
    n = 8 if lod == "full" else 4
    prof += [(rt + wall + (rc - rt - wall) * (1 - math.cos(math.pi * i / n)) / 2,
              L + ch["convergent_length"] * i / n) for i in range(1, n + 1)]
    top = zc + ch["length"]
    prof += [(rc, top), (0, top)]
    objs.append(parts.lathe(f"{name}_chamber", [(0, L - wall)] + prof, segments=seg,
                            material=mats.get("chamber", "dark_metal")))
    rp, hp = ph["diameter"] / 2, ph["height"]
    objs.append(parts.lathe(f"{name}_powerhead",
                            [(0, top - 0.01), (rp * 0.8, top - 0.01), (rp, top + hp * 0.25),
                             (rp, top + hp * 0.8), (rp * 0.6, top + hp), (0, top + hp)],
                            segments=seg, material=mats.get("powerhead", "dark_metal")))
    if "gimbal" in e:
        g = e["gimbal"]
        objs.append(parts.cylinder(f"{name}_gimbal", g["diameter"] / 2, g["height"] + 0.01,
                                   location=(0, 0, top + hp - 0.01), segments=seg // 2,
                                   material=mats.get("parts", "dark_metal")))
    if lod == "full":
        pm = mats.get("parts", "dark_metal")
        for p in e.get("parts", []):
            k, pn = p["kind"], f"{name}_{p['name']}"
            if k == "pump":
                r, l = p["diameter"] / 2, p["length"]
                cap = min(r * 0.6, l / 3)
                objs.append(parts.lathe(pn, [(0, 0), (r * 0.7, 0), (r, cap), (r, l - cap),
                                             (r * 0.7, l), (0, l)],
                                        location=p["at"], direction=p.get("axis", (0, 0, 1)),
                                        segments=24, material=pm))
            elif k == "pipe":
                objs.append(parts.tube(pn, p["points"], p["diameter"] / 2, segments=12,
                                       bend_radius=p.get("bend_radius", p["diameter"]), material=pm))
            elif k == "box":
                objs.append(parts.box(pn, p["size"], location=p["at"], material=pm))
            elif k == "actuator":
                objs.append(parts.strut(pn, p["from"], p["to"], radius=p["diameter"] / 2,
                                        segments=10, material=pm))
            else:
                raise ValueError(f"{pn}: unknown engine part kind {k!r}")
    return objs

# --- Jet -------------------------------------------------------------------------------

def _blade(name, r0, r1, z, chord, pitch, angle, thickness, material):
    """A flat fan blade from radius r0 to r1 at height z, its chord set `pitch` off the
    plane of rotation, turned `angle` about the axis."""
    bm = bmesh.new()
    vs = []
    for r in (r0, r1):
        for c in (-chord / 2, chord / 2):
            for t in (-thickness / 2, thickness / 2):
                # tangential (y) and axial (z) parts of the chord, plus thickness across it
                y = c * math.cos(pitch) - t * math.sin(pitch)
                dz = c * math.sin(pitch) + t * math.cos(pitch)
                vs.append(bm.verts.new((r, y, z + dz)))
    idx = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    for f in idx:
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return parts._object(name, bm, material, Matrix.Rotation(angle, 4, "Z"))

def _jet(name, e, lod):
    nc, fan = e["nacelle"], e["fan"]
    mats = e.get("materials", {})
    seg = 64 if lod == "full" else 20
    L, R = nc["length"], nc["max_diameter"] / 2
    ri, rx = nc["inlet_diameter"] / 2, nc["exit_diameter"] / 2
    wall = nc.get("wall", 0.03)
    if "profile" in nc:
        outer = [(r * R, z * L) for r, z in nc["profile"]]
    else:
        # Rounded lip at the inlet, widest a quarter of the way back, tapering to the exhaust.
        outer = [(rx, 0.0)] + [(rx + (R - rx) * math.sin(math.pi / 2 * i / 6), L * 0.75 * i / 6)
                               for i in range(1, 7)]
        outer += [(R - (R - ri - wall) * (1 - math.cos(math.pi / 2 * i / 4)), L * 0.75 + L * 0.25 * i / 4)
                  for i in range(1, 5)]
    inner = [(max(r - wall, 0.01), z) for r, z in reversed(outer)]
    objs = [parts.lathe(f"{name}_nacelle", outer + inner, closed=True, segments=seg,
                        material=mats.get("nacelle", "white_paint"))]
    zf = L - fan["depth"]
    rh = fan["hub_diameter"] / 2
    sp = e.get("spinner", {"length": rh})
    objs.append(parts.lathe(f"{name}_spinner",
                            [(0, zf - 0.05), (rh, zf - 0.05), (rh, zf)] +
                            [(rh * math.cos(math.pi / 2 * i / 6), zf + sp["length"] * math.sin(math.pi / 2 * i / 6))
                             for i in range(1, 7)],
                            segments=seg // 2, material=mats.get("spinner", "dark_metal")))
    fm = mats.get("fan", "dark_metal")
    if lod == "full":
        for i in range(fan["blades"]):
            objs.append(_blade(f"{name}_fan_blade_{i:02d}", rh * 0.95, fan["diameter"] / 2 - 0.01,
                               zf - fan["chord"] / 2, fan["chord"], math.radians(fan["pitch_deg"]),
                               2 * math.pi * i / fan["blades"], 0.01, fm))
    else:
        objs.append(parts.cylinder(f"{name}_fan", fan["diameter"] / 2 - 0.01, 0.02,
                                   location=(0, 0, zf - 0.02), segments=seg, material=fm))
    # Core: a disc closing the fan duct behind the fan, and the exhaust cone behind the core.
    core = e.get("core")
    if core:
        rcx = core["exit_diameter"] / 2
        objs.append(parts.lathe(f"{name}_core",
                                [(0, -core["plug_length"]), (rcx * 0.3, -core["plug_length"] * 0.9),
                                 (rcx, 0.0), (rcx, zf - fan["chord"] - 0.02), (rh, zf - fan["chord"] - 0.02),
                                 (0, zf - fan["chord"] - 0.02)],
                                segments=seg // 2, material=mats.get("core", "dark_metal")))
    return objs

# --- Building and placing --------------------------------------------------------------

def build(e, name, lod="full"):
    """Build the engine `e` (an "engine" block) at the origin in its own frame. Returns its
    objects."""
    e = _v(e)
    if lod not in ("full", "simple"):
        raise ValueError(f"lod must be 'full' or 'simple', not {lod!r}")
    if e["kind"] == "rocket":
        return _rocket(name, e, lod)
    if e["kind"] == "jet":
        return _jet(name, e, lod)
    raise ValueError(f"unknown engine kind {e['kind']!r}")

def place(e, name, location=(0, 0, 0), direction=(0, 0, 1), roll_deg=0.0, lod="simple"):
    """Build the engine `e` and move it so its exit centre is at `location` and its thrust axis
    (exit to top) points along `direction`. For a vehicle's engines, `direction` is usually
    up the vehicle: (0, 0, 1) for a rocket standing on its engines."""
    m = parts.frame(location, direction, roll_deg)
    objs = build(e, name, lod)
    for o in objs:
        o.matrix_world = m @ o.matrix_world
    return objs
