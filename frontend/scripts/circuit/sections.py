# Which schematic section (a titled rectangle) each part sits in.
import re, sys, json
t = open(sys.argv[1]).read()
rects = [tuple(map(float, m.groups())) for m in re.finditer(r'\n\t\(rectangle\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)', t)]
rects = [(min(a,c),min(b,d),max(a,c),max(b,d)) for a,b,c,d in rects]
texts = []
for m in re.finditer(r'\(text "([^"]+)"', t):
    a = re.search(r'\(at ([-\d.]+) ([-\d.]+)', t[m.end():m.end() + 600])
    texts.append((m.group(1), float(a.group(1)), float(a.group(2))))
def inside(r, x, y): return r[0] <= x <= r[2] and r[1] <= y <= r[3]
def area(r): return (r[2]-r[0])*(r[3]-r[1])
titles = {}
for s, x, y in texts:
    if s.isupper() or s in ("RP2040", "+3.3V LDO", "USB-C", "EXP8"):
        own = [r for r in rects if inside(r, x, y) and r[3] - r[1] > 12]  # not a title banner
        if own: titles[min(own, key=area)] = s
out = {}
for m in re.finditer(r'\n\t\(symbol\s*\(lib_id "([^"]+)"\)\s*\(at ([-\d.]+) ([-\d.]+)(.*?)\n\t\)', t, re.S):
    lib, x, y, body = m.group(1), float(m.group(2)), float(m.group(3)), m.group(4)
    ref = re.search(r'\(property "Reference" "([^"]+)"', body).group(1)
    if ref.startswith("#"): continue
    own = [r for r in rects if inside(r, x, y) and r in titles]
    out[ref] = titles[min(own, key=area)] if own else None
print(json.dumps(dict(sorted(out.items())), indent=0))
