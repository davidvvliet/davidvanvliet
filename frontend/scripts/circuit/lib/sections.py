# Which section of an imported board's schematic each part is drawn in. Designers group parts in
# titled boxes ("USB-C", "CRYSTAL"...); those boxes become the board's blocks.
#   python3 -m lib.sections <schematic.kicad_sch>    prints {reference: section title or null}
import json, re, sys

def sections(path):
    t = open(path).read()
    # Only the sheet's own boxes: symbols draw rectangles too, one tab deeper, in lib_symbols.
    rects = [tuple(map(float, m.groups())) for m in
             re.finditer(r'\n\t\(rectangle\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)', t)]
    rects = [(min(a, c), min(b, d), max(a, c), max(b, d)) for a, b, c, d in rects]
    rects = [r for r in rects if r[3] - r[1] > 12]  # boxes, not the thin banners some titles sit in
    texts = []
    for m in re.finditer(r'\n\t\(text "([^"]+)"', t):
        a = re.search(r'\(at ([-\d.]+) ([-\d.]+)', t[m.end():m.end() + 600])
        texts.append((m.group(1), float(a.group(1)), float(a.group(2))))
    inside = lambda r, x, y: r[0] <= x <= r[2] and r[1] <= y <= r[3]
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    box_of = lambda x, y: min((r for r in rects if inside(r, x, y)), key=area, default=None)
    # A box's title: its topmost text (y grows down), among the texts whose own box it is.
    titles = {}
    for s, x, y in sorted(texts, key=lambda s: (s[2], s[1])):
        r = box_of(x, y)
        if r and r not in titles and "\n" not in s:
            titles[r] = s
    out = {}
    for m in re.finditer(r'\n\t\(symbol\s*\(lib_id "[^"]+"\)\s*\(at ([-\d.]+) ([-\d.]+)(.*?)\n\t\)', t, re.S):
        ref = re.search(r'\(property "Reference" "([^"]+)"', m.group(3)).group(1)
        if ref.startswith("#"):
            continue  # power symbols
        x, y = float(m.group(1)), float(m.group(2))
        own = [r for r in rects if inside(r, x, y) and r in titles]
        out[ref] = titles[min(own, key=area)] if own else None
    return dict(sorted(out.items()))

if __name__ == "__main__":
    print(json.dumps(sections(sys.argv[1]), indent=0))
