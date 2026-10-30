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

if __name__ == "__main__":
    scd4x(); sgp41(); epd154(); zjy128()
