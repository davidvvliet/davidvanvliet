# Writes the 3D models in this folder (VRML, which KiCad reads in 0.1 inch: a 1-unit cube exports as 2.54 mm),
# for parts KiCad's library has no model of. Shapes from the makers' package drawings; sizes without a number
# on the drawing are measured off it, scaled by a dimension that has one. Colours are not sourced unless noted.
#   python3 footprints/models/make.py
# Model frame (KiCad's): mm, x right, y up (towards the top of the footprint, pin 1 is at -x, +y), z up from the board.
import math, os

U = 2.54
HERE = os.path.dirname(os.path.abspath(__file__))

class Mesh:
    def __init__(self): self.shapes = []
    def add(self, rgb, pts, faces, shine=0.0):
        self.shapes.append((rgb, pts, faces, shine))
    def write(self, path, note):
        out = ["#VRML V2.0 utf8", f"# {note}", "# Written by make.py (circuit harness)."]
        for rgb, pts, faces, shine in self.shapes:
            p = ", ".join(f"{x / U:.5f} {y / U:.5f} {z / U:.5f}" for x, y, z in pts)
            f = ", ".join(" ".join(map(str, face)) + " -1" for face in faces)
            out.append(f"Shape {{ appearance Appearance {{ material Material {{ diffuseColor {rgb} shininess {shine} }} }}\n"
                       f"  geometry IndexedFaceSet {{ creaseAngle 0.5 coord Coordinate {{ point [ {p} ] }} coordIndex [ {f} ] }} }}")
        open(path, "w").write("\n".join(out) + "\n")

def rounded(w, h, r, n=8, cx=0.0, cy=0.0, notch=0.0):
    """A rounded rectangle's outline, counter-clockwise from the right; `notch` cuts the top-left corner at 45°."""
    pts = []
    for k, (sx, sy) in enumerate([(1, 1), (-1, 1), (-1, -1), (1, -1)]):
        ox, oy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        if k == 1 and notch:  # top-left: a straight 45° cut instead of an arc
            pts += [(cx - w / 2 + notch, cy + h / 2), (cx - w / 2, cy + h / 2 - notch)]
            continue
        a0 = math.pi / 2 * k
        for i in range(n + 1):
            a = a0 + math.pi / 2 * i / n
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts

def prism(m, rgb, outline, z0, z1, shine=0.0):
    """An upright solid of `outline` from z0 to z1, each face with its own corners so the edges stay sharp
    (shared corners make the viewer blend the light across them: the first box looked smeared)."""
    n = len(outline)
    pts, faces = [], []
    def face(corners):
        faces.append(list(range(len(pts), len(pts) + len(corners)))); pts.extend(corners)
    face([(x, y, z0) for x, y in reversed(outline)])
    face([(x, y, z1) for x, y in outline])
    for i in range(n):
        (ax, ay), (bx, by) = outline[i], outline[(i + 1) % n]
        face([(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)])
    m.add(rgb, pts, faces, shine)

def loft(m, rgb, rings, cap_top=True, shine=0.0):
    """Rings of equal length [(outline, z), ...] joined bottom to top; the top closed with a flat face."""
    n = len(rings[0][0])
    pts = [(x, y, z) for ring, z in rings for x, y in ring]
    faces = [[j * n + i, j * n + (i + 1) % n, (j + 1) * n + (i + 1) % n, (j + 1) * n + i]
             for j in range(len(rings) - 1) for i in range(n)]
    m.add(rgb, pts, faces, shine)
    if cap_top:
        ring, z = rings[-1]
        m.add(rgb, [(x, y, z) for x, y in ring], [list(range(n))], shine)

def disc(m, rgb, cx, cy, d, z, n=24):
    m.add(rgb, [(cx + d / 2 * math.cos(2 * math.pi * i / n), cy + d / 2 * math.sin(2 * math.pi * i / n), z) for i in range(n)],
          [list(range(n))])

def scd4x():
    """Sensirion SCD4x datasheet v1.7, Figure 3 p24: base 10.1 x 10.1 mm, 0.8 thick; cap 8.5 at the base narrowing
    to 7.8, 5.5 tall above the base; "A circular mark and a notched corner of the protective membrane serve as
    polarity marks"; "The white protective membrane on top of the sensor must not be removed". Measured off Figure 3
    (scaled by the 10.1 mm base): cap corner radius 1.6, its top edge rounded about 0.8, membrane 5.2 square with a
    1.6 notch, standing about 0.3; pin-1 mark 0.65 across, 0.65 from the base's corner."""
    m = Mesh()
    prism(m, "0.12 0.28 0.16", rounded(10.1, 10.1, 0.05, n=1), 0, 0.8)
    top, h, fillet = 0.8 + 5.5, 5.5, 0.8
    rings = []
    for z in (0.8, top - fillet):  # the tapered wall
        t = (z - 0.8) / h
        s = 8.5 + (7.8 - 8.5) * t
        rings.append((rounded(s, s, 1.6 - 0.35 * t), z))
    for i in range(1, 5):  # the rounded top edge
        a = math.pi / 2 * i / 4
        s = 7.8 - 2 * fillet * (1 - math.cos(a))
        rings.append((rounded(s, s, max(0.25, 1.25 - fillet * (1 - math.cos(a)))), top - fillet + fillet * math.sin(a)))
    loft(m, "0.82 0.82 0.80", rings, shine=0.3)
    prism(m, "0.96 0.96 0.94", rounded(5.2, 5.2, 0.3, n=4, notch=1.6), top, top + 0.3)
    disc(m, "0.85 0.85 0.85", -10.1 / 2 + 0.65, 10.1 / 2 - 0.65, 0.65, 0.8 + 0.01)
    m.write(os.path.join(HERE, "Sensirion_SCD4x.wrl"), "Sensirion SCD4x CO2 sensor (scd4x datasheet v1.7, Figure 3, p24)")

def sgp41():
    """Sensirion SGP41 datasheet v1.0, Figure 17 p18: body 2.44 x 2.44 x 0.85 mm, "over-molded by a black,
    epoxy-based mold compound"; "The sensor opening with a typical diameter of 0.8 mm is offset to the bottom right
    corner on the top side"; terminals 0.4 wide, 0.35 long from the side wall and 0.15 thick, a "Ni/Pd/Au plated
    copper lead frame" (side walls diced, unplated). Measured off Figure 17 (scaled by the 2.44 mm body): opening centre 1.51 from the left
    and 1.58 from the top; pin-1 dot 0.28 across at 0.27, 0.38."""
    m = Mesh()
    prism(m, "0.06 0.06 0.06", rounded(2.44, 2.44, 0.02, n=1), 0, 0.85)
    for sx in (-1, 1):  # the terminals, showing at the side walls (standing 0.01 proud so they don't fight the wall)
        for y in (-0.8, 0, 0.8):
            prism(m, "0.75 0.72 0.65", rounded(0.36, 0.4, 0.01, n=1, cx=sx * (2.44 / 2 - 0.17), cy=y), 0, 0.15, shine=0.5)
    disc(m, "0.25 0.25 0.27", -2.44 / 2 + 1.51, 2.44 / 2 - 1.58, 0.8, 0.85 + 0.005)
    disc(m, "0.6 0.6 0.6", -2.44 / 2 + 0.27, 2.44 / 2 - 0.38, 0.28, 0.85 + 0.005)
    m.write(os.path.join(HERE, "Sensirion_SGP41.wrl"), "Sensirion SGP41 VOC sensor (sgp41 datasheet v1.0, Figure 17, p18)")

def epd154():
    """Waveshare 1.54inch e-Paper V2 datasheet, 1.4 Mechanical Drawing p5: "TFT OD 37.32" x "TFT OD 31.80", "Total
    1.05" thick; "TFT AA 27.00" square, 2.40 from the far edge and from the side (so centred across the 31.80);
    FPC 0.10 thick, "FPC+PI stiffener Total Thickness 0.30", 24 contacts at 0.50 pitch, 12.50 wide at its end;
    the tail reaches 14.30 from the glass (bottom view). Drawn here flat (its "Bending Area" unbent), its end
    inserted 0.5 mm past the connector's origin, so it sits on this footprint's Hirose FH12 (estimated: Hirose's
    drawing wasn't readable). The tail centred on the edge: estimated off the front view."""
    m = Mesh()
    end, tail, L, W = -0.5, 14.30, 37.32, 31.80   # model y is up: the panel lies towards -y, away from the pins
    g0 = end - tail
    prism(m, "0.78 0.62 0.25", [(6.25, end), (-6.25, end), (-6.25, g0), (6.25, g0)], 0.35, 0.45, shine=0.3)  # FPC
    prism(m, "0.70 0.52 0.18", [(6.25, end), (-6.25, end), (-6.25, end - 3.5), (6.25, end - 3.5)], 0.25, 0.55)  # stiffener
    prism(m, "0.55 0.56 0.55", [(W / 2, g0), (-W / 2, g0), (-W / 2, g0 - L), (W / 2, g0 - L)], 0, 1.05, shine=0.2)  # glass
    a1 = g0 - L + 2.40
    prism(m, "0.86 0.86 0.83", [(13.5, a1 + 27), (-13.5, a1 + 27), (-13.5, a1), (13.5, a1)], 1.05, 1.06)  # active area
    m.write(os.path.join(HERE, "Waveshare_EPD_1.54in.wrl"), "Waveshare 1.54inch e-Paper V2 panel (datasheet 1.4, p5)")

def zjy128():
    """Zhongjingyuan ZJY128R-IG01 1.28" round TFT, drawing ZJY128R-IG01 (2019-07-10, in Elecrow's 1.28 inch round LCD
    datasheet, p4): glass "35.2±0.15 (LCD)" round, "37.24±0.15 (LCD)" long to its flat at the FPC; backlight 35.60 x
    38.10; "1.50±0.1" thick; "32.40 (LCD A.A)" centred, 1.60 inside the glass; FPC 11.4 wide, "12.24±0.3" past the
    glass, 0.13 thick, 12 contacts at 0.7 pitch. Folded under the panel as the drawing's bent view ("0.50Max"), its
    contacts on the board's pads at the origin. The neck's width (14) is measured off the drawing, scaled by the
    35.2 glass; the glass stands 0.35 above the board on the fold (estimated)."""
    m = Mesh()
    edge, cy, r = 10.7, -8.94, 17.6          # model y is up: the panel's flat edge at +10.7, its centre at -8.94
    # glass, polariser and backlight: the disc and the neck to the flat as two convex solids (VRML draws faces convex)
    prism(m, "0.08 0.08 0.09", [(r * math.cos(2 * math.pi * i / 64), cy + r * math.sin(2 * math.pi * i / 64)) for i in range(64)],
          0.35, 1.85, shine=0.4)
    y0 = cy + math.sqrt(r * r - 7 * 7)
    prism(m, "0.08 0.08 0.09", [(7, edge), (-7, edge), (-7, y0 - 1), (7, y0 - 1)], 0.35, 1.849, shine=0.4)
    disc(m, "0.02 0.02 0.03", 0, cy, 32.4, 1.86, n=64)                    # display area
    prism(m, "0.78 0.62 0.25", [(5.7, edge), (-5.7, edge), (-5.7, -1.0), (5.7, -1.0)], 0, 0.13, shine=0.3)  # FPC under the glass
    prism(m, "0.78 0.62 0.25", [(5.7, edge + 0.3), (-5.7, edge + 0.3), (-5.7, edge), (5.7, edge)], 0, 1.0, shine=0.3)  # its fold
    prism(m, "0.85 0.70 0.30", [(4.0, 1.0), (-4.0, 1.0), (-4.0, -1.0), (4.0, -1.0)], 0.13, 0.14, shine=0.6)  # contacts
    m.write(os.path.join(HERE, "ZJY128R-IG01.wrl"), "Zhongjingyuan ZJY128R-IG01 1.28in round TFT (drawing ZJY128R-IG01, p4)")

def tps2121():
    """TI TPS2120/TPS2121 datasheet SLVSEA3F, package outline RUX0012A (VQFN-HR), p. "PACKAGE OUTLINE": body
    "2.1"/"1.9" by "2.6"/"2.4" (2.0 x 2.5 drawn), "1 MAX" tall (drawn at the maximum: no nominal given); the
    four power terminals "4X 0.95"/"0.75" long and "4X 0.45"/"0.25" wide (0.85 x 0.35 drawn) on the short
    sides, 0.7 apart ("2X 0.7"); the eight small ones "8X 0.5"/"0.3" long and "8X 0.25"/"0.15" wide (0.4 x 0.2)
    at 0.5 pitch ("6X 0.5") on the long sides. Terminals drawn 0.1 thick ("(0.1) TYP", read as their thickness:
    estimated). Mould colour not sourced. Pin 1 (top left, -x +y) is the "PIN 1 INDEX AREA"."""
    m = Mesh()
    prism(m, "0.10 0.10 0.10", rounded(2.0, 2.5, 0.02, n=1), 0, 1.0)
    for sx in (-1, 1):
        for y in (-0.35, 0.35):
            prism(m, "0.75 0.72 0.65", rounded(0.85, 0.35, 0.01, n=1, cx=sx * (1.0 - 0.425 + 0.01), cy=y), 0, 0.1, shine=0.5)
    for sy in (-1, 1):
        for x in (-0.75, -0.25, 0.25, 0.75):
            prism(m, "0.75 0.72 0.65", rounded(0.2, 0.4, 0.01, n=1, cx=x, cy=sy * (1.25 - 0.2 + 0.01)), 0, 0.1, shine=0.5)
    disc(m, "0.6 0.6 0.6", -0.6, 0.85, 0.3, 1.0 + 0.005)
    m.write(os.path.join(HERE, "TI_VQFN-HR-12_RUX.wrl"), "TI TPS2121 VQFN-HR-12 (RUX0012A, datasheet SLVSEA3F)")

def vfbga178():
    """ST VFBGA178 (STM32N6), DS14791 Rev 11 Table 134: body "12.00 BSC" square, "A" max "1.00" tall, ball standoff
    "A1" min "0.21", balls "b" typ "0.43" at "e" "0.80"; the balls from symbols/stm32n657_vfbga178.json.
    Drawn: body from 0.25 (standoff, estimate between A1 min and the ball's height) to 1.0; balls as short
    cylinders. A1 marked by a dot at the top-left corner (Table 134 note 8). Colours not sourced."""
    import json
    rows = "ABCDEFGHJKLMNP"
    balls = json.load(open(os.path.join(HERE, "..", "..", "symbols", "stm32n657_vfbga178.json")))["balls"]
    m = Mesh()
    prism(m, "0.10 0.10 0.10", rounded(12.0, 12.0, 0.05, n=1), 0.25, 1.0)
    for b in balls:
        x, y = -5.2 + (int(b[1:]) - 1) * 0.8, 5.2 - rows.index(b[0]) * 0.8
        cyl(m, "0.80 0.80 0.80", x, y, 0.43, 0.0, 0.25, n=8, shine=0.5)
    disc(m, "0.6 0.6 0.6", -5.0, 5.0, 0.6, 1.0 + 0.005)
    m.write(os.path.join(HERE, "ST_VFBGA-178.wrl"), "ST VFBGA178 (STM32N6, datasheet DS14791 Rev 11)")

def rgt16():
    """TI RGT0016C VQFN-16 (TPS62130 datasheet SLVSAG7F, package outline): body "3.1"/"2.9" square (3.0 drawn),
    "1.0"/"0.8" tall (1.0 drawn, the maximum), 16 terminals "0.30"/"0.18" wide (0.24 drawn) at "0.5" pitch, 0.4 long
    (estimate) and 0.1 thick (estimate). Pin 1 dot top left. Colours not sourced."""
    m = Mesh()
    prism(m, "0.10 0.10 0.10", rounded(3.0, 3.0, 0.02, n=1), 0, 1.0)
    for i in range(4):
        x = -0.75 + 0.5 * i
        for sx, sy, w, h, cx, cy in ((1, 0, 0.4, 0.24, 1.5 - 0.2 + 0.01, -x), (-1, 0, 0.4, 0.24, -(1.5 - 0.2 + 0.01), x),
                                      (0, 1, 0.24, 0.4, x, 1.5 - 0.2 + 0.01), (0, -1, 0.24, 0.4, x, -(1.5 - 0.2 + 0.01))):
            prism(m, "0.75 0.72 0.65", rounded(w, h, 0.01, n=1, cx=cx, cy=cy), 0, 0.1, shine=0.5)
    disc(m, "0.6 0.6 0.6", -1.0, 1.0, 0.3, 1.0 + 0.005)
    m.write(os.path.join(HERE, "TI_RGT0016C.wrl"), "TI VQFN-16 RGT0016C (TPS6213x)")

def xfl4020():
    """Coilcraft XFL4020 inductor: "4×4×2.1" (TPS62130 datasheet SLVSAG7F Table 9-3). Drawn as a 4 x 4 mm block
    2.1 tall with slightly rounded corners. Colour not sourced."""
    m = Mesh()
    prism(m, "0.22 0.22 0.22", rounded(4.0, 4.0, 0.3, n=3), 0, 2.1)
    m.write(os.path.join(HERE, "Coilcraft_XFL4020.wrl"), "Coilcraft XFL4020 (4 x 4 x 2.1 mm)")

def cyl(m, rgb, cx, cy, d, z0, z1, n=48, shine=0.0):
    prism(m, rgb, [(cx + d / 2 * math.cos(2 * math.pi * i / n), cy + d / 2 * math.sin(2 * math.pi * i / n)) for i in range(n)], z0, z1, shine)

def lathe(m, rgb, profile, n=96, shine=0.0, cx=0.0, cy=0.0):
    """A surface of revolution about z from `profile` [(r, z), ...]. Each step of the profile is its own band
    (sharp where the profile turns, smooth around)."""
    for (ra, za), (rb, zb) in zip(profile, profile[1:]):
        ring = lambda r: [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        loft(m, rgb, [(ring(ra), za), (ring(rb), zb)], cap_top=False, shine=shine)

def ribbed(m, rgb, r, z0, z1, ribs, depth, groove=0.35, smooth=None, inner=None, shine=0.0, smooth_rgb=None):
    """A grip ring of radius r from z0 to z1: `ribs` flat-bottomed grooves `depth` deep, each `groove` of the
    pitch wide, cut into it. `smooth` (centre angle, half width, degrees) leaves an arc plain (where a ring is
    printed), drawn in `smooth_rgb` so a texture can find it. Built from quads only (KiCad fills convex faces)."""
    inner = inner if inner is not None else r - depth - 0.5
    def plain(a):
        if not smooth: return False
        d = (math.degrees(a) - smooth[0] + 180) % 360 - 180
        return abs(d) <= smooth[1]
    seg = []  # (a0, a1, radius) around the ring
    for k in range(ribs):
        a0 = 2 * math.pi * k / ribs; a1 = 2 * math.pi * (k + 1) / ribs; ag = a0 + (a1 - a0) * groove
        if plain((a0 + a1) / 2):
            seg += [(a0 + (a1 - a0) * i / 4, a0 + (a1 - a0) * (i + 1) / 4, r, True) for i in range(4)]
        else:
            seg += [(a0, ag, r - depth, False)] + [(ag + (a1 - ag) * i / 3, ag + (a1 - ag) * (i + 1) / 3, r, False) for i in range(3)]
    P = lambda a, rr: (rr * math.cos(a), rr * math.sin(a))
    groups = {}
    for i, (a0, a1, rr, pl) in enumerate(seg):
        col = smooth_rgb if pl and smooth_rgb else rgb
        pts, faces = groups.setdefault(col, ([], []))
        def face(c):
            faces.append(list(range(len(pts), len(pts) + len(c)))); pts.extend(c)
        (x0, y0), (x1, y1) = P(a0, rr), P(a1, rr)
        face([(x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)])                       # outside
        (u0, v0), (u1, v1) = P(a0, inner), P(a1, inner)
        face([(u0, v0, z1), (x0, y0, z1), (x1, y1, z1), (u1, v1, z1)])                       # top
        face([(u1, v1, z0), (x1, y1, z0), (x0, y0, z0), (u0, v0, z0)])                       # bottom
        nr = seg[(i + 1) % len(seg)][2]
        if nr != rr:                                                                         # groove wall
            (a, b), (c, d) = P(a1, rr), P(a1, nr)
            face([(a, b, z0), (c, d, z0), (c, d, z1), (a, b, z1)] if nr < rr else [(c, d, z0), (a, b, z0), (a, b, z1), (c, d, z1)])
    for col, (pts, faces) in groups.items():
        m.add(col, pts, faces, shine)

def radial(m, sub, angle_deg, r, z):
    """Copies the Mesh `sub` (built along +z from its origin) onto a ring at radius r, height z, pointing outwards."""
    a = math.radians(angle_deg); c, s = math.cos(a), math.sin(a)
    for rgb, pts, faces, shine in sub.shapes:   # local z -> outwards, local x -> along the ring's axis (z), y -> tangent
        m.add(rgb, [((r + pz) * c - py * s, (r + pz) * s + py * c, z + px) for px, py, pz in pts], faces, shine)

def thumb_screw(head_d=3.2, head_h=2.6, shank_d=2.0, shank_h=1.6, ribs=14):
    """A knurled thumb screw standing on +z (shank first), with a slot across its head."""
    s = Mesh()
    lathe(s, STEEL, [(shank_d / 2, -0.5), (shank_d / 2, shank_h)], n=24, shine=0.6)
    ribbed(s, DARKSTEEL, head_d / 2, shank_h, shank_h + head_h, ribs, 0.2, groove=0.4, inner=0.0, shine=0.5)
    prism(s, "0.05 0.05 0.05", rounded(head_d * 0.95, 0.45, 0.01, n=1), shank_h + head_h - 0.5, shank_h + head_h + 0.01)  # slot
    return s

BLACK, GREEN = "0.06 0.06 0.06", "0.10 0.42 0.22"  # black sampled off the hood's unlit side (photo below), the GS
                                                    # camera's green board unsourced (the lens guide draws it green)
STEEL, DARKSTEEL, CHROME, GOLD = "0.62 0.62 0.60", "0.36 0.36 0.35", "0.80 0.80 0.78", "0.80 0.68 0.35"
# Faces a texture goes on (recipe "screens") carry their own colours, close to the black, so the packer can find them.
LENS_FOCUS_PRINT, LENS_APERTURE_PRINT, LENS_BLUE, LENS_GLASS = "0.07 0.06 0.06", "0.06 0.07 0.06", "0.09 0.52 0.69", "0.03 0.06 0.08"

def gs_camera():
    """Raspberry Pi Global Shutter Camera, mechanical drawing RP-008195 (lying lens up: z up is the lens axis, the
    back plate on z = 0; model -y is the side the ribbon tab hangs off). Depths from the side view, measured off it
    and checked against its printed numbers (scaled by the 25.07 overall): front cylinder "ø30.75" 5.8 deep ("5.8"),
    knurled back-focus ring "ø36" 1.2 deep ("1.2"), mount body 10.2 deep (ø30.75 drawn; its outline is hidden in
    the front view), board "38" square, 1.4 thick ("1.4"), back plate "39.5" square with "R4.75" corners, 6.49
    deep ("6.49"; its curved back drawn as a taper, estimated); lens opening "ø22.4" with the 8.5 square sensor
    window ("8.5"). Holes "ø2.5", "4" in from the edges. The lock-screw block on top: "10.16" wide, 5.4 tall and
    "5.02" deep, measured; its thumb screw like the lens's (Waveshare's photo of the camera with the lens shows
    one), sized by estimate. The ribbon tab: "13.97" wide, reaching 11.3 past the board edge and "7.62" deep
    (measured). The back-focus ring's grip (60 ribs) and the edge rounding are estimated from that photo. Heights
    of the board's own parts are not drawn and left out."""
    m = Mesh()
    z_board = 6.49; z_body = z_board + 1.4; z_ring = 25.07 - 7.0; z_front = 25.07 - 5.8
    loft(m, BLACK, [(rounded(33.0, 33.0, 4.0), 0.0), (rounded(37.6, 37.6, 4.6), 1.2), (rounded(39.5, 39.5, 4.75), 3.0),
                    (rounded(39.5, 39.5, 4.75), z_board - 0.4), (rounded(39.1, 39.1, 4.55), z_board)], shine=0.3)
    prism(m, GREEN, rounded(38, 38, 1.0), z_board, z_body, shine=0.2)
    for x in (-15, 15):
        for y in (-15, 15):
            disc(m, GOLD, x, y, 5.0, z_body + 0.005, n=32)
            lathe(m, "0.02 0.02 0.02", [(1.25, z_body + 0.02), (1.25, z_board - 0.1)], n=24, cx=x, cy=y)   # the hole's wall
            disc(m, "0.01 0.01 0.01", x, y, 2.5, z_body + 0.01, n=24)
    lathe(m, BLACK, [(30.75 / 2, z_body), (30.75 / 2, z_ring)], shine=0.3)
    ribbed(m, BLACK, 18.0, z_ring, z_front, 60, 0.45, groove=0.45, inner=15.0, shine=0.3)               # back-focus ring
    lathe(m, BLACK, [(30.75 / 2, z_front), (30.75 / 2, 25.07 - 0.4), (30.75 / 2 - 0.4, 25.07), (22.4 / 2, 25.07),
                     (22.4 / 2, 25.07 - 4.0), (9.0, 25.07 - 5.0)], shine=0.3)                       # front face and bore
    disc(m, "0.01 0.01 0.01", 0, 0, 18.0, 25.07 - 5.0, n=48)
    prism(m, "0.12 0.14 0.18", rounded(8.5, 8.5, 0.1, n=1), 25.07 - 12.0, 25.07 - 4.99, shine=0.6)   # sensor window
    prism(m, BLACK, rounded(10.16, 5.4, 0.6, n=3, cy=19.0 + 2.2 - 2.7), 25.07 - 12.02, z_ring, shine=0.3)  # lock-screw block
    radial(m, thumb_screw(), 90, 19.0 + 2.2 - 2.7 + 2.7, z_ring - 2.6)
    prism(m, BLACK, rounded(13.97, 11.3 + 4.0, 0.6, n=3, cy=-19.0 - 11.3 / 2 + 2.0), z_body, 25.07 - 7.0, shine=0.3)
    prism(m, "0.85 0.85 0.82", rounded(12.0, 0.6, 0.05, n=1, cy=-19.0 - 11.3 + 0.7), 25.07 - 7.0 - 3.2, 25.07 - 7.0 - 1.6)  # cable slot
    m.write(os.path.join(HERE, "RPi_GS_Camera.wrl"), "Raspberry Pi Global Shutter Camera (drawing RP-008195)")

def lens16():
    """The 16 mm C-mount lens Raspberry Pi sells for its cameras, "Φ39.00 × 50.00mm" (retailer listings: Waveshare,
    Farnell, raspberrypi.dk; Raspberry Pi publishes no drawing). Profile measured off Waveshare's side-on product
    photo (waveshare.com/16mm-telephoto-lens-for-pi.htm, image -1), scaled by the hood's 39 mm (583 px): front to
    the chrome flange 49.2 mm (the listing's 50, 1.6 % short). From the flange up: chrome ring ø33.2 2.7 high,
    aperture ring ø35.1 z 3.0-14.7, aperture scale band ø34.1 to 20.9, focus ring ø35.0 to 31.8, blue band ø33.9
    to 35.5, a cone from ø30.9 to ø38.2 at 40.8, the hood ø39 to 49.2. Lock screws at z 7.0 (aperture) and 27.4
    (focus), the index dot at 12.8, all on one side; the printing's place and size from the same photo (see
    boards/star-tracker-hat/markings.py). Estimated from the other photos (-3 to -5): rib count and depth, the
    hood's wall and inner steps, the glass's size and depth, the screws' size. The C-CS adapter under it ("C-CS
    adapter included", GS brief): 5 thick and 30.75 across, estimated. The thread below the flange sits inside the
    adapter and is left out. z = 0 sits on the camera's front face; the printed side faces model -y."""
    m = Mesh()
    F = -90  # the printed side's angle (degrees about z)
    ribbed(m, BLACK, 30.75 / 2, 0, 5.0, 72, 0.3, groove=0.5, inner=12.8, shine=0.3)       # C-CS adapter, fine knurl
    z = 5.0
    lathe(m, CHROME, [(12.8, z), (33.2 / 2 - 0.3, z), (33.2 / 2, z + 0.3), (33.2 / 2, z + 2.4), (33.2 / 2 - 0.3, z + 2.7),
                      (16.2, z + 2.7)], shine=0.9)
    lathe(m, BLACK, [(16.2, z + 2.7), (16.2, z + 3.0)])
    ribbed(m, BLACK, 35.1 / 2, z + 3.0, z + 14.7, 30, 0.5, inner=16.0, shine=0.3)            # aperture ring
    ribbed(m, BLACK, 34.1 / 2, z + 14.7, z + 20.9, 24, 0.0, smooth=(F, 180), smooth_rgb=LENS_APERTURE_PRINT, inner=16.0, shine=0.3)
    ribbed(m, BLACK, 35.0 / 2, z + 20.9, z + 31.8, 30, 0.5, smooth=(F, 55), smooth_rgb=LENS_FOCUS_PRINT, inner=16.0, shine=0.3)
    lathe(m, LENS_BLUE, [(16.0, z + 31.8), (33.9 / 2 - 0.2, z + 31.8), (33.9 / 2, z + 32.0), (33.9 / 2, z + 35.3),
                         (33.9 / 2 - 0.2, z + 35.5), (15.45, z + 35.5)], shine=0.6)        # blue band
    lathe(m, BLACK, [(15.45, z + 35.5), (19.1, z + 40.8), (19.5, z + 41.2), (19.5, z + 48.8), (19.2, z + 49.2),
                     (17.9, z + 49.2), (17.9, z + 46.5), (17.2, z + 46.0), (17.2, z + 44.0), (13.0, z + 41.5)], shine=0.3)
    disc(m, "0.02 0.02 0.02", 0, 0, 26.0, z + 41.49, n=96)
    lathe(m, LENS_GLASS, [(12.6, z + 41.5), (9.0, z + 42.3), (4.5, z + 42.7), (0.0, z + 42.8)], shine=1.0)  # front glass
    for zc in (z + 7.0, z + 27.4):
        r = 35.1 / 2 if zc < z + 14.7 else 35.0 / 2
        radial(m, thumb_screw(), F, r - 0.2, zc)
    dot = Mesh(); disc(dot, "0.92 0.92 0.90", 0, 0, 0.9, 0.0, n=16)
    radial(m, dot, F, 35.1 / 2 + 0.02, z + 12.8)
    m.write(os.path.join(HERE, "Lens_16mm_C.wrl"), "16 mm C-mount lens (retailer size; profile from Waveshare's photo)")

def baffle_design(a, half_fov, exclusion, depth, margin):
    """A 1-stage stray-light baffle in front of the lens, to the rule in Rohrbach, "Corrected Recursive Equations for
    Vane Aperture Sizes and Locations in One- and Two-Stage Stray Light Baffle Systems" (NASA GSFC, SPIE 2023,
    ntrs.nasa.gov/citations/20230011280): "the inner walls of the baffle are not simultaneously visible to both
    stray light sources and the optical entrance pupil". Built by the geometric construction, in one meridional
    section (z from the pupil plane, radius r): vane edges on the field of view's edge plus `margin` ("a positive
    margin ... to all the back-end baffle radii"; 0.25 mm, its "standard +0.25 / -0.00 mm tolerance"); the entrance
    far enough out that light at the exclusion angle past its edge misses the pupil; each next vane where the pupil
    stops seeing the wall that light (at the exclusion angle or more, past the vanes before it) reaches.
    Returns (length, wall radius, [(z, edge radius), ...] from the entrance in), after checking the rule on 2000
    wall points against rays from the whole pupil and every angle from the exclusion angle to 89.5°."""
    t, T = math.tan(math.radians(half_fov)), math.tan(math.radians(exclusion))
    h = lambda z: a + margin + z * t
    L = 2 * (a + margin) / (T - t)
    R = h(L) + depth
    vanes = [L]
    while True:
        v = vanes[-1]
        s_max = min([(h(v) + h(w)) / (w - v) for w in vanes[:-1]], default=math.inf)  # steepest light past this vane
        if s_max < T: break
        z_lit = v - (R - h(v)) / s_max                # the wall is lit from here down
        if z_lit <= 0: break
        vanes.append(z_lit * (2 * a + margin) / (R + a - z_lit * t))   # the pupil sees no wall below z_lit
    def clear(p, q):
        (y0, z0), (y1, z1) = p, q
        return all(not (min(z0, z1) < v < max(z0, z1)) or abs(y0 + (y1 - y0) * (v - z0) / (z1 - z0)) <= h(v) + 1e-9 for v in vanes)
    for i in range(1, 2000):
        zw = L * i / 2000
        seen = any(clear((-a + 2 * a * k / 50, 0), (R, zw)) for k in range(51))
        lit = any(abs(y) <= h(L) and clear((y, L), (R, zw)) for y in
                  (R - (L - zw) * math.tan(math.radians(exclusion + (89.5 - exclusion) * k / 59)) for k in range(60)))
        assert not (seen and lit), f"baffle: wall at z {zw:.2f} is both seen and lit"
    return L, R, [(v, h(v)) for v in vanes]

def star_tracker_baffle():
    """The star tracker's baffle (baffle_design), over the 16 mm lens's hood, z = 0 at its front glass. Inputs: the
    pupil radius 12.6 (the front glass, estimated from Waveshare's photos: the lens's real entrance pupil and glass
    sizes are not published), half field 11.09° (the sensor's diagonal half, 1456 x 1088 pixels of 3.45 µm per
    Raspberry Pi's camera documentation, over the nominal 16 mm), Sun exclusion 30° (Rohrbach's example, and the
    University of Colorado's star-tracker baffle project), vanes 4 deep. The vanes 1 thick with a 0.25 knife edge
    and a 45° bevel (Rohrbach's model; the bevel's side is chosen, he sets it by Fest's formula), the tube's 1.5
    wall and the plate on the hood (hole ø39.4) are estimates. Flat black inside (his "Flat Black Paint")."""
    L, R, vanes = baffle_design(12.6, 11.09, 30, 4.0, 0.25)
    print(f"baffle: length {L:.1f}, inner ø{2 * R:.1f}, vanes " + ", ".join(f"z {z:.1f} ø{2 * r:.1f}" for z, r in vanes))
    m = Mesh(); W = 1.5
    lathe(m, BAFFLE_BLACK, [(19.7, -2.0), (R + W, -2.0), (R + W, L), (R, L), (R, 0.0), (19.7, 0.0), (19.7, -2.0)], n=96)
    for z, r in vanes:   # knife edge at z facing the sky, bevel on the lens side
        lathe(m, BAFFLE_BLACK, [(R, z), (r, z), (r, z - 0.25), (r + 0.75, z - 1.0), (R, z - 1.0)], n=96)
    m.write(os.path.join(HERE, "Baffle_StarTracker.wrl"), "Star tracker baffle (vanes per Rohrbach 2023's rule)")

BAFFLE_BLACK = "0.03 0.03 0.03"

def pi_zero2w():
    """Raspberry Pi Zero 2 W from its mechanical drawing: "65" x "30", holes "3.5" in from the edges, the corners
    rounded 3 (measured). Parts on top measured off the drawing (scaled by its 65 and 30; its port centres "12.4",
    "41.4" and "54" came out 12.45, 41.4 and 54.0): x/y in mm from the left and top edges. Heights, board thickness
    (1.6) and colours are not in Raspberry Pi's documents: estimated. The 40-pin header is KiCad's model, added
    beside this one. Model frame: x right, y up (the board's top edge at y = 0), the board's underside at z = 0."""
    m = Mesh()
    t = 1.6
    prism(m, GREEN, rounded(65, 30, 3.0, cx=32.5, cy=-15), 0, t, shine=0.2)
    for x in (3.5, 61.5):
        for y in (3.5, 26.5):
            disc(m, "0.80 0.68 0.35", x, -y, 6.0, t + 0.005); disc(m, "0.02 0.02 0.02", x, -y, 2.75, t + 0.01)
    def box(rgb, x0, x1, y0, y1, h, shine=0.0):
        prism(m, rgb, [(x1, -y1), (x1, -y0), (x0, -y0), (x0, -y1)][::-1], t, t + h, shine)
    box("0.10 0.10 0.11", 19.9, 34.9, 8.4, 23.5, 1.2, 0.3)       # the big centre chip
    box("0.72 0.72 0.74", 37.6, 50.0, 10.3, 22.5, 1.6, 0.6)      # the metal can
    box("0.15 0.15 0.16", 1.7, 13.1, 7.1, 19.1, 1.4, 0.2)        # the left part
    box("0.72 0.72 0.74", 7.0, 17.9, 23.2, 30.6, 3.0, 0.6)       # left port (centre "12.4")
    box("0.72 0.72 0.74", 37.6, 45.2, 25.3, 31.2, 2.6, 0.6)      # port (centre "41.4")
    box("0.72 0.72 0.74", 50.2, 57.8, 25.3, 31.2, 2.6, 0.6)      # port (centre "54")
    box("0.12 0.12 0.12", 61.6, 65.0, 7.0, 23.1, 1.2, 0.2)       # camera connector
    for x0, x1, y0, y1 in ((13.9, 16.3, 12.1, 15.4), (20.8, 22.7, 25.4, 28.2), (52.2, 54.2, 6.5, 8.1),
                           (55.9, 58.4, 11.8, 13.8), (54.0, 57.0, 15.2, 18.2)):
        box("0.12 0.12 0.12", x0, x1, y0, y1, 0.8)
    oc = [(52.85 + 2.05 * math.cos(math.pi / 8 + i * math.pi / 4), -22.05 + 2.05 * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)]
    prism(m, "0.20 0.20 0.21", oc, t, t + 2.0)                    # the octagonal part
    m.write(os.path.join(HERE, "RPi_Zero_2W.wrl"), "Raspberry Pi Zero 2 W (mechanical drawing; heights estimated)")

def zero_camera_cable(path, w=11.5):
    """The Zero's camera cable as a flat strip along `path` [(x, z), ...] (mm, in its own frame, y across): 11.5
    wide (PCN 36: "the width has been reduced from 16 mm to 11.5 mm" for most of a 22-to-15-way cable's length;
    the Zero cable's own width is not published) and 0.14 thick (the standard cable drawing: conductor 0.027,
    insulation 0.055 a side)."""
    m = Mesh(); th = 0.14
    for (xa, za), (xb, zb) in zip(path, path[1:]):
        dx, dz = xb - xa, zb - za; L = math.hypot(dx, dz); nx, nz = -dz / L * th / 2, dx / L * th / 2
        q = [(xa - nx, za - nz), (xb - nx, zb - nz), (xb + nx, zb + nz), (xa + nx, za + nz)]
        pts, faces = [], []
        for y in (-w / 2, w / 2):
            pts += [(x, y, z) for x, z in q]
        faces = [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
        m.add("0.82 0.80 0.74", pts, faces, 0.3)
    return m

def star_tracker_cable():
    """The star-tracker HAT's camera cable: from the Pi's camera connector (its top 1.2 above the Pi, at the board's
    edge) out and up into the camera's ribbon tab, as placed in boards/star-tracker-hat/recipe.json. Frame: x from
    the Pi's right edge, z up from the Pi's underside."""
    zc = 1.6 + 1.2
    zero_camera_cable([(-1.7, zc), (3.0, zc), (9.0, zc + 8.5), (12.3, zc + 8.5)]).write(
        os.path.join(HERE, "Cable_StarTracker.wrl"), "Pi Zero camera cable (star-tracker HAT placement)")

def star_tracker_n6_cable():
    """star-tracker-n6's camera cable: the standard 15-way cable ("Width W 16.000 mm", drawing RP-008146) from the
    board's camera socket (J3, contacts 1.0 mm high per KiCad's TE 1-84952-5) out past the board's edge and up into
    the camera's ribbon tab, as placed in boards/star-tracker-n6/recipe.json. Frame: x along the cable from the
    socket's contacts, z up from the board's top surface."""
    zc, zs = 0.5, -1.6 + 25.07 - 7.0 - 2.4
    zero_camera_cable([(0.0, zc), (10.0, zc), (17.0, zs), (22.5, zs)], w=16.0).write(
        os.path.join(HERE, "Cable_StarTrackerN6.wrl"), "Raspberry Pi camera cable, 16 mm (star-tracker-n6 placement)")

def hat_standoffs():
    """The four M2.5 standoffs and screws holding the star-tracker HAT on the Pi Zero, at the holes both boards share
    ("3.5" in from the edges of the 65 x 30 outline, both drawings). Frame: the HAT's, x right, y up from its top-left
    corner, z up from its top surface. The stack follows recipe.json's attachments: the Pi's underside 14.24 below the
    HAT's top, both boards 1.6 thick, so each standoff spans the 11.04 between them. Standoff 5 across flats, brass;
    pan-head screws 4.5 across, 1.7 tall, steel, on the HAT's top: estimates (common hardware, no
    source read)."""
    m = Mesh(); t, pi_under = 1.6, -14.24
    hexagon = lambda cx, cy: [(cx + 2.5 / math.cos(math.pi / 6) * math.cos(math.pi / 6 + i * math.pi / 3),
                               cy + 2.5 / math.cos(math.pi / 6) * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)]
    for x in (3.5, 61.5):
        for y in (-3.5, -26.5):
            prism(m, "0.78 0.62 0.30", hexagon(x, y), pi_under + t, -t, shine=0.6)
            # a screw head on the HAT's top; under the Pi the mount's standoffs carry on (tracker_bracket)
            lathe(m, "0.70 0.70 0.72", [(0.0, 0.0), (2.25, 0.0), (2.25, 1.2), (1.9, 1.7), (0.0, 1.7)], n=24, cx=x, cy=y, shine=0.5)
    m.write(os.path.join(HERE, "Standoffs_StarTrackerHAT.wrl"), "M2.5 standoffs and screws (star-tracker HAT on a Pi Zero)")

BRACKET_BLACK = "0.07 0.07 0.08"

def tracker_bracket(name, note, holes, under, cam, cam_holes_along, baffle_z, plate, top_screws=False):
    """A mount holding a star tracker's board, camera and baffle in one frame (the model frame of the board it is
    attached to: x right, y up, z up from the board's top). A base plate `plate` (x0, y0, x1, y1) 3 thick, its top
    6 below `under` (the lowest board's underside: the Pi Zero's parts reach 2.54 below it, make.pi_zero2w), with:
    a 6-long M2.5 standoff and a screw under the plate at each board hole in `holes` (plus a screw head on the
    board's top when `top_screws`); the camera on two 6-long risers at its back plate's two "ø2.5" holes ("7.56" in
    from the sides of the "39.5" plate: 12.19 from the axis, along model x or y as `cam_holes_along`), its back on
    the risers at `under`; the baffle held by a clamp ring round its tube (the baffle's 60.1 inner and 1.5 wall,
    star_tracker_baffle) at `baffle_z`, on four ø6 posts on the diagonals 38 from the camera's axis, clear of the
    camera's 25.96 corner radius, its ribbon tab (13.97 wide) and lock screw on the axes. Drawing RP-008195 for the
    camera's holes; plate and ring thickness, post size, the 6 mm gaps and the finish (black anodised) are estimates:
    the design is ours, not from a document."""
    m = Mesh(); cx, cy = cam; top = under - 6.0; bot = top - 3.0
    prism(m, BRACKET_BLACK, rounded(plate[2] - plate[0], plate[3] - plate[1], 4.0, cx=(plate[0] + plate[2]) / 2,
                                    cy=(plate[1] + plate[3]) / 2), bot, top, shine=0.25)
    def head(x, y, flat, dome):
        k = 1 if dome > flat else -1
        lathe(m, "0.70 0.70 0.72", [(0.0, flat), (2.25, flat), (2.25, dome - k * 0.5), (1.9, dome), (0.0, dome)], n=24, cx=x, cy=y, shine=0.5)
    hexagon = lambda x, y: [(x + 2.5 / math.cos(math.pi / 6) * math.cos(math.pi / 6 + i * math.pi / 3),
                             y + 2.5 / math.cos(math.pi / 6) * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)]
    for x, y in holes:
        prism(m, "0.78 0.62 0.30", hexagon(x, y), top, under, shine=0.6)
        head(x, y, bot, bot - 1.7)
        if top_screws: head(x, y, 0.0, 1.7)
    for d in (-12.19, 12.19):
        x, y = (cx + d, cy) if cam_holes_along == "x" else (cx, cy + d)
        cyl(m, BRACKET_BLACK, x, y, 6.0, top, under, n=24, shine=0.25)
        head(x, y, bot, bot - 1.7)
    ring_in, ring_out, post_r = 60.1 / 2 + 1.5, 41.0, 38.0
    lathe(m, BRACKET_BLACK, [(ring_in, baffle_z), (ring_out, baffle_z), (ring_out, baffle_z + 4.0), (ring_in, baffle_z + 4.0), (ring_in, baffle_z)], n=96, cx=cx, cy=cy, shine=0.25)
    for a in (45, 135, 225, 315):
        px, py = cx + post_r * math.cos(math.radians(a)), cy + post_r * math.sin(math.radians(a))
        cyl(m, BRACKET_BLACK, px, py, 6.0, top, baffle_z, n=24, shine=0.25)
        head(px, py, bot, bot - 1.7); head(px, py, baffle_z + 4.0, baffle_z + 5.7)
    m.write(os.path.join(HERE, name), note)

def tracker_brackets():
    # star-tracker HAT (recipe attachments): Pi underside 14.24 below the HAT's top, camera turned 90 at (107.6, -15),
    # baffle base at 57.33; the Pi's holes as hat_standoffs.
    tracker_bracket("Bracket_StarTrackerHAT.wrl", "Star tracker mount (star-tracker HAT on a Pi Zero)",
                    [(x, y) for x in (3.5, 61.5) for y in (-3.5, -26.5)], -14.24, (107.6, -15.0), "y", 57.33,
                    (-3.0, -46.0, 152.0, 16.0))
    # star-tracker-n6 (recipe): 80 x 53 board, holes 3.5 in from each edge, its underside 1.6 below its top; camera
    # turned 180 at (35, -95), baffle base at 69.97.
    tracker_bracket("Bracket_StarTrackerN6.wrl", "Star tracker mount (star-tracker-n6)",
                    [(x, y) for x in (3.5, 76.5) for y in (-3.5, -49.5)], -1.6, (35.0, -95.0), "x", 69.97,
                    (-3.0, -140.0, 83.0, 3.0), top_screws=True)

def rnx12():
    """TI RNX0012B VQFN-HR (LMR36006-Q1 datasheet SNVSAY7D p46): body "2.1"/"1.9" by "3.1"/"2.9" (2 x 3 drawn), "0.9"/"0.8"
    tall (0.9 drawn); terminals "0.3"/"0.2" wide (0.25) and "0.5"/"0.3" long (0.4), placed as the land pattern (p47);
    pin 12 a bar "1.725"/"1.525" long (1.625). Terminal thickness 0.1 and the colours are estimates. Model frame y up."""
    m = Mesh()
    prism(m, "0.10 0.10 0.10", rounded(2.0, 3.0, 0.02, n=1), 0, 0.9)
    term = lambda cx, cy, w, h: prism(m, "0.75 0.72 0.65", rounded(w, h, 0.01, n=1, cx=cx, cy=cy), 0, 0.1, shine=0.5)
    for y in (1.125, 0.475, -0.175, -0.675):
        term(-0.8, y, 0.4, 0.25); term(0.8, y, 0.4, 0.25)
    for x in (-0.5, 0.0, 0.5): term(x, -1.3, 0.25, 0.4)
    term(0.0, 0.8125, 0.25, 1.625)
    disc(m, "0.6 0.6 0.6", -0.6, 1.1, 0.25, 0.9 + 0.005)
    m.write(os.path.join(HERE, "TI_RNX0012B.wrl"), "TI VQFN-HR RNX0012B (LMR36006-Q1)")

if __name__ == "__main__":
    scd4x(); sgp41(); epd154(); zjy128(); tps2121(); gs_camera(); lens16(); pi_zero2w(); star_tracker_cable(); star_tracker_baffle(); star_tracker_n6_cable(); hat_standoffs(); tracker_brackets(); rnx12(); vfbga178(); rgt16(); xfl4020()
